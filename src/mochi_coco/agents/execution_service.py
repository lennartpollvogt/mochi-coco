"""
Agent execution service for managing agent chat sessions and orchestrating
the two-phase planning + execution loop.

This module provides the AgentExecutionService which handles:
- Creating and loading agent chat sessions in ``./agents/agent_chats/``
- Refreshing system prompts from SKILL.md on each invocation
- Loading ephemeral prompt templates (planning / execution)
- Executing agent tool calls through the existing tool pipeline
- Formatting the final output returned to the main LLM

Agent chats reuse the existing ``ChatSession`` JSON schema so that
serialisation, migration, and message handling are fully consistent
with user-LLM chats.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Mapping, Optional

from ollama import ChatResponse, Tool

from ..chat.session import ChatSession, SessionMessage
from ..tools.config import ToolSettings
from ..tools.execution_service import ToolExecutionResult, ToolExecutionService
from ..tools.schema_service import ToolSchemaService
from .discovery_service import AgentDefinition, AgentDiscoveryService
from .prompt_loader import load_execution_prompt, load_planning_prompt

logger = logging.getLogger(__name__)

# Directory where agent chat sessions are persisted
AGENT_CHATS_DIR = "./agents/agent_chats"


class AgentExecutionService:
    """
    Service that manages agent chat sessions and runs the two-phase
    planning + execution loop.

    Each agent invocation either creates a new ``ChatSession`` (stored in
    ``./agents/agent_chats/``) or continues an existing one.  The system
    prompt is always refreshed from the agent's ``SKILL.md`` so that
    changes take effect immediately.
    """

    def __init__(
        self,
        client: Any,
        tool_settings: Optional[ToolSettings] = None,
        context_window_service: Any = None,
    ):
        """
        Initialise the execution service.

        Args:
            client: An ``OllamaClient`` instance used for LLM requests.
            tool_settings: Tool execution policy (confirmation rules).
                Falls back to ``ALWAYS_CONFIRM`` when *None*.
            context_window_service: Optional ``ContextWindowService`` for
                context-window management of agent sessions.
        """
        self.client = client
        self.tool_settings = tool_settings or ToolSettings()
        self.context_window_service = context_window_service
        self.schema_service = ToolSchemaService()
        self._discovery = AgentDiscoveryService()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_or_load_session(
        self,
        agent_definition: AgentDefinition,
        session_id: Optional[str] = None,
    ) -> ChatSession:
        """
        Create a new agent chat session or load an existing one.

        When *session_id* is provided the session file in
        ``./agents/agent_chats/`` is loaded and its system prompt is
        refreshed from the agent's current ``SKILL.md``.  When omitted a
        brand-new session is created.

        Args:
            agent_definition: The resolved ``AgentDefinition`` for the
                target agent.
            session_id: Optional session ID for continuation.  Pass an
                empty string or ``None`` to start a new session.

        Returns:
            A ``ChatSession`` ready for use.
        """
        # Ensure the agent chats directory exists
        chats_dir = Path(AGENT_CHATS_DIR)
        chats_dir.mkdir(parents=True, exist_ok=True)

        # Determine the model to use (agent model → fallback to metadata model)
        model = agent_definition.model or "unknown"

        if session_id:
            session = ChatSession(
                model=model,
                session_id=session_id,
                sessions_dir=str(chats_dir),
            )
            # load_session is called automatically in ChatSession.__init__
            # when a session_id is provided.  Refresh the system prompt so
            # that SKILL.md changes take effect immediately.
            self.refresh_system_prompt(session, agent_definition)
            logger.info(
                "Loaded existing agent session '%s' for agent '%s'",
                session_id,
                agent_definition.name,
            )
        else:
            session = ChatSession(
                model=model,
                session_id=None,  # auto-generate
                sessions_dir=str(chats_dir),
            )
            # Set the initial system prompt
            self.refresh_system_prompt(session, agent_definition)
            logger.info(
                "Created new agent session '%s' for agent '%s'",
                session.session_id,
                agent_definition.name,
            )

        return session

    def refresh_system_prompt(
        self,
        session: ChatSession,
        agent_definition: AgentDefinition,
    ) -> None:
        """
        Replace the system prompt in *session* with the latest content
        from the agent's ``SKILL.md``.

        This is called on every invocation so that edits to ``SKILL.md``
        (including model changes) take effect immediately without
        restarting the application.

        Args:
            session: The agent chat session to update.
            agent_definition: Agent definition containing the latest
                system prompt text.
        """
        prompt_content = agent_definition.system_prompt
        if not prompt_content:
            logger.warning(
                "Agent '%s' has an empty system prompt", agent_definition.name
            )
            return

        session.update_system_message(
            content=prompt_content,
            source_file=f"agents/{agent_definition.name}/SKILL.md",
        )
        logger.debug("Refreshed system prompt for agent '%s'", agent_definition.name)

    # ------------------------------------------------------------------
    # Message helpers
    # ------------------------------------------------------------------

    def add_user_instruction(self, session: ChatSession, instruction: str) -> None:
        """
        Append the calling LLM's instruction as a ``user`` message.

        Inside agent chats the *calling LLM* has role ``user`` and the
        *agent* has role ``assistant`` (spec §6.3).

        Args:
            session: The agent chat session.
            instruction: The instruction text from the main LLM.
        """
        session.add_user_message(content=instruction)

    def add_assistant_message(
        self,
        session: ChatSession,
        response: ChatResponse,
        model: str,
    ) -> None:
        """
        Persist an agent (assistant) response to the session.

        This handles plain-text responses that do **not** contain tool
        calls.  For responses *with* tool calls use
        :meth:`add_tool_call_message` instead.

        Args:
            session: The agent chat session.
            response: The ``ChatResponse`` from Ollama.
            model: Model name that produced the response.
        """
        message = SessionMessage(
            role="assistant",
            content=response.message.content or "",
            model=model,
            eval_count=getattr(response, "eval_count", None),
            prompt_eval_count=getattr(response, "prompt_eval_count", None),
        )
        session.messages.append(message)
        session.metadata.message_count = len(session.messages)
        session.metadata.updated_at = datetime.now().isoformat()
        session.save_session()

    def add_tool_call_message(
        self,
        session: ChatSession,
        response: ChatResponse,
        model: str,
    ) -> None:
        """
        Persist an assistant message that contains tool calls.

        The tool-call data is stored in exactly the same format as
        user-LLM chats (spec §9).

        Args:
            session: The agent chat session.
            response: The ``ChatResponse`` whose ``message.tool_calls``
                is non-empty.
            model: Model name that produced the response.
        """
        tool_calls_data = []
        for tc in response.message.tool_calls or []:
            tool_calls_data.append(
                {
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                        if tc.function.arguments
                        else {},
                    }
                }
            )

        message = SessionMessage(
            role="assistant",
            content=response.message.content or "",
            model=model,
            tool_calls=tool_calls_data,
            eval_count=getattr(response, "eval_count", None),
            prompt_eval_count=getattr(response, "prompt_eval_count", None),
        )
        session.messages.append(message)
        session.metadata.message_count = len(session.messages)
        session.metadata.updated_at = datetime.now().isoformat()
        session.save_session()

    def add_tool_response(
        self,
        session: ChatSession,
        tool_name: str,
        result: ToolExecutionResult,
    ) -> None:
        """
        Persist a tool response message in the agent chat session.

        Mirrors ``ToolAwareRenderer._add_tool_response_to_session``.

        Args:
            session: The agent chat session.
            tool_name: Name of the tool that was called.
            result: The execution result.
        """
        content = result.result if result.success else f"Error: {result.error_message}"
        tool_msg = SessionMessage(
            role="tool",
            content=content or "",
            model=None,
        )
        tool_msg.tool_name = tool_name

        session.messages.append(tool_msg)
        session.metadata.message_count = len(session.messages)
        session.metadata.updated_at = datetime.now().isoformat()
        session.save_session()

    # ------------------------------------------------------------------
    # Prompt template helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_planning_prompt() -> str:
        """Return the ephemeral planning prompt (not persisted)."""
        return load_planning_prompt()

    @staticmethod
    def get_execution_prompt() -> str:
        """Return the ephemeral execution prompt (not persisted)."""
        return load_execution_prompt()

    # ------------------------------------------------------------------
    # API request helpers
    # ------------------------------------------------------------------

    def build_messages_with_ephemeral(
        self,
        session: ChatSession,
        ephemeral_user_message: str,
    ) -> List[Mapping[str, Any]]:
        """
        Build the message list for an API request, appending an
        ephemeral ``user`` message that is **not** persisted.

        Args:
            session: The agent chat session.
            ephemeral_user_message: Extra instruction to append (e.g.
                planning or execution prompt).

        Returns:
            List of message dicts suitable for ``client.chat()``.
        """
        messages = session.get_messages_for_api()
        messages.append({"role": "user", "content": ephemeral_user_message})

        logger.debug(
            f"Built {len(messages)} messages for API request. Last 3 messages: "
            f"{[{k: v[:100] if k == 'content' and isinstance(v, str) else v for k, v in msg.items()} for msg in messages[-3:]]}"
        )

        return messages

    def get_agent_tools_as_ollama(
        self, agent_definition: AgentDefinition
    ) -> List[Tool]:
        """
        Convert an agent's tool functions to Ollama ``Tool`` objects.

        Args:
            agent_definition: The agent whose tools to convert.

        Returns:
            List of ``Tool`` objects ready for ``client.chat(tools=…)``.
        """
        if not agent_definition.tools:
            return []

        tool_schemas = self.schema_service.convert_functions_to_tools(
            agent_definition.tools
        )
        return list(tool_schemas.values())

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def execute_agent_tool(
        self,
        tool_call: Any,
        agent_definition: AgentDefinition,
        confirm_callback: Optional[Callable] = None,
    ) -> ToolExecutionResult:
        """
        Execute a single tool call from the agent.

        Uses the existing ``ToolExecutionService`` so that execution
        policy and confirmation flow are identical to user-LLM tool
        calls (spec §11).

        Args:
            tool_call: A tool call object from the ``ChatResponse``.
            agent_definition: The agent that owns the tool.
            confirm_callback: Optional callback for user confirmation.

        Returns:
            ``ToolExecutionResult`` with success status and output.
        """
        tool_name = tool_call.function.name
        arguments = tool_call.function.arguments or {}

        if tool_name not in agent_definition.tools:
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message=f"Tool '{tool_name}' not found in agent '{agent_definition.name}'",
                tool_name=tool_name,
            )

        execution_service = ToolExecutionService(agent_definition.tools)
        return execution_service.execute_tool(
            tool_name,
            arguments,
            self.tool_settings.execution_policy,
            confirm_callback,
        )

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    def format_agent_output(
        self,
        session: ChatSession,
        instruction_index: int,
    ) -> str:
        """
        Format the final output returned by the ``agent`` tool to the
        main LLM.

        The output starts with ``Session ID: <id>`` on the first line,
        followed by all agent messages (assistant, tool-call, and
        tool-response) from *instruction_index* to the end of the
        session (spec §12).

        Args:
            session: The agent chat session.
            instruction_index: Index of the ``user`` message that
                contained the LLM's instruction.  All messages after
                this index are included in the output.

        Returns:
            Plain-text output string.
        """
        lines: list[str] = [f"Session ID: {session.session_id}"]

        for msg in session.messages[instruction_index + 1 :]:
            if msg.role == "assistant":
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    # Summarise tool calls
                    for tc in list(tool_calls):
                        fn = tc.get("function", {})
                        tc_name = fn.get("name", "unknown")
                        tc_args = fn.get("arguments", {})
                        lines.append(f"[Tool Call] {tc_name}({tc_args})")
                if msg.content:
                    lines.append(msg.content)

            elif msg.role == "tool":
                tool_name = getattr(msg, "tool_name", "unknown")
                lines.append(f"[Tool Result: {tool_name}] {msg.content}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Resolve agent definition
    # ------------------------------------------------------------------

    def resolve_agent(
        self,
        agent_name: str,
        enabled_agent_names: List[str],
    ) -> Optional[AgentDefinition]:
        """
        Look up and validate an agent by name.

        Args:
            agent_name: The requested agent name (from the tool call).
            enabled_agent_names: Names currently enabled in the session.

        Returns:
            The ``AgentDefinition`` if valid and enabled, else ``None``.
        """
        if agent_name not in enabled_agent_names:
            logger.warning(
                "Agent '%s' is not in enabled list %s",
                agent_name,
                enabled_agent_names,
            )
            return None

        definitions = self._discovery.discover_agents()
        defn = definitions.get(agent_name)

        if defn is None:
            logger.warning("Agent '%s' not found during discovery", agent_name)
            return None

        if not defn.valid:
            logger.warning("Agent '%s' is invalid: %s", agent_name, defn.error_message)
            return None

        return defn

    # ------------------------------------------------------------------
    # Main entry-point  (skeleton — loop logic added in Step 6)
    # ------------------------------------------------------------------

    def execute_agent(
        self,
        agent_name: str,
        instruction: str,
        session_id: str = "",
        enabled_agent_names: Optional[List[str]] = None,
        session_model: Optional[str] = None,
        confirm_callback: Optional[Callable[[str, dict], bool]] = None,
    ) -> str:
        """
        Execute an agent invocation end-to-end.

        This is the main entry-point called when the LLM invokes the
        ``agent`` tool.  It performs:

        1. Agent resolution and validation
        2. Session creation / loading with system prompt refresh
        3. Planning phase (no tools, ephemeral planning prompt)
        4. Execution phase (tools allowed, ephemeral execution prompt,
           loop on tool calls)
        5. Output formatting

        Args:
            agent_name: Name of the agent to invoke.
            instruction: The task instruction from the main LLM.
            session_id: Optional session ID for continuation.
            enabled_agent_names: Currently enabled agents in the session.
            session_model: The user-session model (fallback when agent
                model is unavailable).
            confirm_callback: Optional callback for tool execution confirmation.

        Returns:
            Plain-text output starting with ``Session ID: <id>``.
        """
        enabled_agent_names = enabled_agent_names or []

        # 1. Resolve agent
        agent_def = self.resolve_agent(agent_name, enabled_agent_names)
        if agent_def is None:
            return (
                f"Error: Agent '{agent_name}' is not available. "
                f"Enabled agents: {', '.join(enabled_agent_names)}"
            )

        # Use agent model, fallback to session model
        model = agent_def.model or session_model or "unknown"

        # 2. Create or load session
        try:
            session = self.create_or_load_session(
                agent_def,
                session_id=session_id if session_id else None,
            )
        except Exception as e:
            logger.error(f"Failed to create/load agent session: {e}", exc_info=True)
            return f"Error: Failed to initialize agent session: {e}"

        # Ensure the model on the session matches
        session.model = model
        session.metadata.model = model

        # 3. Add instruction
        instruction_index = len(session.messages)
        self.add_user_instruction(session, instruction)

        # Calculate context window if available
        context_window = None
        if self.context_window_service:
            try:
                context_decision = (
                    self.context_window_service.calculate_optimal_context_window(
                        session, model
                    )
                )
                context_window = context_decision.new_context_window
                logger.debug(
                    f"Agent context window: {context_window} tokens - {context_decision.reason.value}"
                )
            except Exception as e:
                logger.warning(f"Failed to calculate agent context window: {e}")

        # ── Phase 1: Planning (no tools) ──
        logger.info(f"Agent '{agent_name}': Starting planning phase")
        try:
            planning_messages = self.build_messages_with_ephemeral(
                session, self.get_planning_prompt()
            )

            logger.debug(
                f"Agent '{agent_name}': Calling chat_stream for planning - "
                f"model: {model}, messages: {len(planning_messages)}, "
                f"context_window: {context_window}, tools: None"
            )

            # Request without tools
            planning_stream = self.client.chat_stream(
                model=model,
                messages=planning_messages,
                context_window=context_window,
            )

            # Collect planning response
            planning_content = ""
            final_planning_chunk = None
            chunk_count = 0
            for chunk in planning_stream:
                chunk_count += 1
                if chunk.message and chunk.message.content:
                    planning_content += chunk.message.content
                final_planning_chunk = chunk

            logger.info(
                f"Agent '{agent_name}': Planning phase collected {len(planning_content)} chars from {chunk_count} chunks"
            )

            # Save planning response to session
            if final_planning_chunk and planning_content.strip():
                self.add_assistant_message(session, final_planning_chunk, model)
                logger.debug(
                    f"Agent '{agent_name}': Planning response saved ({len(planning_content)} chars)"
                )
            else:
                logger.warning(
                    f"Agent '{agent_name}': Empty planning response - "
                    f"final_chunk: {final_planning_chunk is not None}, "
                    f"content: '{planning_content}'"
                )

        except Exception as e:
            logger.error(
                f"Agent '{agent_name}': Planning phase failed: {e}", exc_info=True
            )
            return (
                f"Error: Agent planning phase failed: {e}\n\n"
                f"Session ID: {session.session_id}"
            )

        # ── Phase 2: Execution (tools allowed, loop on tool calls) ──
        logger.info(f"Agent '{agent_name}': Starting execution phase")
        agent_tools = self.get_agent_tools_as_ollama(agent_def)
        max_iterations = 10  # Safety limit to prevent infinite loops
        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1
                logger.debug(
                    f"Agent '{agent_name}': Execution iteration {iteration}/{max_iterations}"
                )

                # Build messages with ephemeral execution prompt
                execution_messages = self.build_messages_with_ephemeral(
                    session, self.get_execution_prompt()
                )

                logger.debug(
                    f"Agent '{agent_name}': Calling chat_stream for execution iter {iteration} - "
                    f"model: {model}, messages: {len(execution_messages)}, "
                    f"context_window: {context_window}, tools: {len(agent_tools) if agent_tools else 0}"
                )

                if agent_tools:
                    import json

                    logger.debug(
                        f"Agent '{agent_name}': Tool schema (first 2 tools): "
                        f"{json.dumps([t if isinstance(t, dict) else str(t) for t in agent_tools[:2]], indent=2)}"
                    )

                # Request with tools
                execution_stream = self.client.chat_stream(
                    model=model,
                    messages=execution_messages,
                    tools=agent_tools if agent_tools else None,
                    context_window=context_window,
                )

                # Collect execution response
                execution_content = ""
                tool_calls = []
                final_execution_chunk = None
                exec_chunk_count = 0

                for chunk in execution_stream:
                    exec_chunk_count += 1
                    if chunk.message:
                        if chunk.message.content:
                            execution_content += chunk.message.content
                        # Capture tool calls from the chunk
                        if (
                            hasattr(chunk.message, "tool_calls")
                            and chunk.message.tool_calls
                        ):
                            # Merge tool calls (Ollama may send them incrementally)
                            for tc in chunk.message.tool_calls:
                                # Check if this tool call already exists
                                existing = next(
                                    (
                                        t
                                        for t in tool_calls
                                        if hasattr(t, "function")
                                        and hasattr(tc, "function")
                                        and t.function.name == tc.function.name
                                    ),
                                    None,
                                )
                                if not existing:
                                    tool_calls.append(tc)
                    final_execution_chunk = chunk

                logger.info(
                    f"Agent '{agent_name}': Execution iter {iteration} collected {len(execution_content)} chars from {exec_chunk_count} chunks"
                )

                # Check if agent made tool calls
                has_tool_calls = False
                if final_execution_chunk and hasattr(
                    final_execution_chunk.message, "tool_calls"
                ):
                    if final_execution_chunk.message.tool_calls:
                        has_tool_calls = True
                        tool_calls = final_execution_chunk.message.tool_calls

                logger.debug(
                    f"Agent '{agent_name}': Execution iter {iteration} - "
                    f"has_tool_calls: {has_tool_calls}, "
                    f"execution_content: '{execution_content[:100]}...' ({len(execution_content)} chars total)"
                )

                if has_tool_calls and final_execution_chunk:
                    logger.info(
                        f"Agent '{agent_name}': Processing {len(tool_calls)} tool call(s)"
                    )

                    # Save assistant message with tool calls
                    self.add_tool_call_message(session, final_execution_chunk, model)

                    # Execute each tool call
                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        logger.debug(
                            f"Agent '{agent_name}': Executing tool '{tool_name}'"
                        )

                        try:
                            result = self.execute_agent_tool(
                                tool_call, agent_def, confirm_callback
                            )

                            # Add tool response to session
                            if result:
                                self.add_tool_response(session, tool_name, result)
                                if not result.success:
                                    logger.warning(
                                        f"Agent '{agent_name}': Tool '{tool_name}' failed: {result.error_message}"
                                    )
                            else:
                                # Create error result when execution returns None
                                error_result = ToolExecutionResult(
                                    success=False,
                                    result=None,
                                    error_message="Tool execution failed",
                                    tool_name=tool_name,
                                )
                                self.add_tool_response(session, tool_name, error_result)
                                logger.error(
                                    f"Agent '{agent_name}': Tool '{tool_name}' returned no result"
                                )

                        except Exception as e:
                            logger.error(
                                f"Agent '{agent_name}': Tool '{tool_name}' execution error: {e}",
                                exc_info=True,
                            )
                            # Create error result for exception
                            error_result = ToolExecutionResult(
                                success=False,
                                result=None,
                                error_message=str(e),
                                tool_name=tool_name,
                            )
                            self.add_tool_response(session, tool_name, error_result)

                    # Continue loop to process tool results
                    continue

                else:
                    # No tool calls - agent has finished
                    logger.info(
                        f"Agent '{agent_name}': Completed (no tool calls in iteration {iteration}) - "
                        f"final_chunk exists: {final_execution_chunk is not None}, "
                        f"content length: {len(execution_content)}, "
                        f"content: '{execution_content[:200]}...'"
                    )

                    # Save final assistant message
                    if final_execution_chunk and execution_content.strip():
                        logger.info(
                            f"Agent '{agent_name}': Saving final assistant message with {len(execution_content)} chars"
                        )
                        self.add_assistant_message(
                            session, final_execution_chunk, model
                        )
                    else:
                        logger.warning(
                            f"Agent '{agent_name}': Not saving assistant message - "
                            f"final_chunk: {final_execution_chunk is not None}, "
                            f"execution_content: '{execution_content}'"
                        )

                    # Exit loop
                    break

            # Check if we hit iteration limit
            if iteration >= max_iterations:
                logger.warning(
                    f"Agent '{agent_name}': Reached max iterations ({max_iterations})"
                )
                # Add a note to the session
                error_result = ToolExecutionResult(
                    success=False,
                    result=None,
                    error_message=f"Agent execution stopped: maximum iteration limit ({max_iterations}) reached",
                    tool_name="system",
                )
                self.add_tool_response(session, "system", error_result)

        except Exception as e:
            logger.error(
                f"Agent '{agent_name}': Execution phase failed: {e}", exc_info=True
            )
            return (
                f"Error: Agent execution phase failed: {e}\n\n"
                f"Session ID: {session.session_id}"
            )

        # 5. Format and return output
        return self.format_agent_output(session, instruction_index)
