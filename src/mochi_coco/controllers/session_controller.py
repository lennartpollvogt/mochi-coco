"""
Session controller for handling session-specific operations and message processing.

This module extracts session management logic from ChatController to improve
separation of concerns and provide focused session operations.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, NamedTuple, Optional

from ..chat import ChatSession
from ..ollama import OllamaClient
from ..rendering.tool_aware_renderer import ToolAwareRenderer
from ..services import ContextWindowService, SessionManager
from ..services.context_window_service import ContextDecisionReason

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class SessionInitResult(NamedTuple):
    """Result of session initialization."""

    session: Optional[ChatSession]
    model: Optional[str]
    markdown_enabled: bool
    show_thinking: bool
    success: bool


class MessageProcessResult(NamedTuple):
    """Result of message processing."""

    success: bool
    final_chunk: Optional[Any] = None
    error_message: Optional[str] = None


class SessionController:
    """Handles session-specific operations and message processing."""

    def __init__(
        self,
        session_manager: SessionManager,
        client: OllamaClient,
        context_window_service: Optional[ContextWindowService] = None,
    ):
        self.session_manager = session_manager
        self.client = client
        self.context_window_service = context_window_service

    def initialize_session(self) -> SessionInitResult:
        """Initialize a new or existing session."""
        try:
            result = self.session_manager.initialize_session()
            session, model, markdown_enabled, show_thinking, system_prompt = result

            # For new sessions, session will be None initially but model should not be None
            # For existing sessions, both session and model should not be None
            if model is None:
                logger.error("Model is None after initialization")
                return SessionInitResult(None, None, False, False, False)

            # Setup session with system prompt if provided
            session, model = self.session_manager.setup_session(
                session, model, system_prompt
            )

            if session is None or model is None:
                logger.error("Session or model is None after setup")
                return SessionInitResult(None, None, False, False, False)

            return SessionInitResult(
                session, model, markdown_enabled, show_thinking, True
            )

        except Exception as e:
            logger.error(f"Session initialization failed: {e}", exc_info=True)
            return SessionInitResult(None, None, False, False, False)

    def process_user_message(
        self,
        session: ChatSession,
        model: str,
        user_input: str,
        renderer,
        tool_context: Optional[Dict[str, Any]] = None,
    ) -> MessageProcessResult:
        """
        Process a regular user message and get LLM response.

        Args:
            session: Current chat session
            model: Model to use
            user_input: User's input message
            renderer: Renderer to use for output
            tool_context: Optional dict with tool-related context
        """
        try:
            # Add user message to session
            session.add_user_message(content=user_input)

            # Get messages for API
            messages: List[Mapping[str, Any]] = session.get_messages_for_api()

            # Calculate optimal context window for this request
            context_window = None
            if self.context_window_service:
                try:
                    context_decision = (
                        self.context_window_service.calculate_optimal_context_window(
                            session, model
                        )
                    )
                    context_window = context_decision.new_context_window

                    # Log context window decision for debugging
                    if context_decision.should_adjust and context_decision.reason in [
                        ContextDecisionReason.USAGE_THRESHOLD,
                        ContextDecisionReason.INITIAL_SETUP,
                    ]:
                        logger.info(
                            f"Context window increased to {context_window} tokens - {context_decision.reason.value}"
                        )
                    elif logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"Using context window: {context_window} tokens - {context_decision.reason.value}"
                        )

                    # Ensure session metadata has context_window_config initialized
                    if session.metadata:
                        if (
                            not hasattr(session.metadata, "context_window_config")
                            or session.metadata.context_window_config is None
                        ):
                            session.metadata.context_window_config = {
                                "dynamic_enabled": True,
                                "current_window": context_window,
                                "last_adjustment": None,
                                "adjustment_history": [],
                                "manual_override": False,
                            }

                    # Update session metadata with context window decision
                    if session.metadata and session.metadata.context_window_config:
                        session.metadata.context_window_config["current_window"] = (
                            context_window
                        )
                        session.metadata.context_window_config["last_adjustment"] = (
                            context_decision.reason.value
                        )
                        # Add to adjustment history (keep last 10)
                        history = session.metadata.context_window_config.get(
                            "adjustment_history", []
                        )
                        history.append(
                            {
                                "timestamp": datetime.now().isoformat(),
                                "window_size": context_window,
                                "reason": context_decision.reason.value,
                            }
                        )
                        session.metadata.context_window_config["adjustment_history"] = (
                            history[-10:]
                        )

                except Exception as e:
                    logger.warning(f"Failed to calculate context window: {e}")
                    # Fall back to no context window limit
                    context_window = None

            # Check if tools are enabled
            if tool_context and tool_context.get("tools_enabled"):
                # Stream with tool support
                tools = tool_context.get("tools", [])
                text_stream = self.client.chat_stream(
                    model=model,
                    messages=messages,
                    tools=tools,
                    context_window=context_window,
                )

                # Create tool-aware renderer if needed
                if not isinstance(renderer, ToolAwareRenderer):
                    tool_execution_service = tool_context.get("tool_execution_service")
                    renderer = ToolAwareRenderer(renderer, tool_execution_service)

                # Add required context for tool handling
                tool_context.update(
                    {
                        "session": session,
                        "model": model,
                        "client": self.client,
                        "available_tools": tools,
                        "context_window": context_window,
                    }
                )

                final_chunk = renderer.render_streaming_response(
                    text_stream, tool_context
                )
                was_interrupted = (
                    False  # Tool rendering doesn't support interruption yet
                )
            else:
                # Regular streaming with interruption support
                text_stream = self.client.chat_stream(
                    model=model, messages=messages, context_window=context_window
                )
                final_chunk, was_interrupted = (
                    renderer.render_streaming_response_with_interrupt(text_stream)
                )

            # Add message to session if we have content (interrupted or complete)
            if final_chunk and final_chunk.message.content.strip():
                if not tool_context or not tool_context.get("tools_enabled"):
                    # No tools enabled, always add message
                    session.add_message(chunk=final_chunk)
                elif not (
                    hasattr(final_chunk.message, "tool_calls")
                    and final_chunk.message.tool_calls
                ):
                    # Tools enabled but this message has no tool calls, add it
                    session.add_message(chunk=final_chunk)

            return MessageProcessResult(True, final_chunk)

        except Exception as e:
            return MessageProcessResult(False, None, str(e))
