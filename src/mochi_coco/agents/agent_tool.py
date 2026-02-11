"""
Agent tool factory for creating the dynamic `agent` tool function.

This module provides a factory that generates an `agent` callable with a dynamic
docstring listing currently enabled agents and their descriptions. The generated
function is intended to be injected into the tool context alongside regular tools
so that the main LLM can invoke agents as a standard tool call.

Each time the enabled agent list changes, a new function should be generated
(via `create_agent_tool`) so that Ollama's schema conversion picks up the
updated docstring. This also naturally invalidates any cache keyed on `id(func)`.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from .discovery_service import AgentDefinition

logger = logging.getLogger(__name__)


def create_agent_tool(
    enabled_agents: Dict[str, AgentDefinition],
) -> object:
    """
    Factory that builds a fresh ``agent`` callable whose docstring
    dynamically lists the currently enabled agents.

    The returned function has the signature expected by Ollama's
    ``convert_function_to_tool`` utility so it can be passed directly
    to ``client.chat()`` / ``client.chat_stream()`` as a tool.

    Args:
        enabled_agents: Mapping of agent name → AgentDefinition for every
            agent that is currently enabled in the session.

    Returns:
        A callable ``agent(agent, instruction, session_id)`` function
        with a docstring that enumerates the enabled agents.
    """

    # ------------------------------------------------------------------
    # Build the dynamic docstring
    # ------------------------------------------------------------------
    agent_lines: list[str] = []
    for name, defn in enabled_agents.items():
        desc = defn.description or "No description"
        agent_lines.append(f"  - {name}: {desc}")

    agent_list_text = "\n".join(agent_lines) if agent_lines else "  (none)"

    docstring = (
        "Delegate a task to a specialised agent.\n"
        "\n"
        "Use this tool when the task is best handled by one of the available agents.\n"
        "Pick the most appropriate agent based on the descriptions below and provide\n"
        "a clear, self-contained instruction so the agent can complete the task.\n"
        "\n"
        "Available agents:\n"
        f"{agent_list_text}\n"
        "\n"
        "Args:\n"
        "    agent (str): The name of the agent to invoke. Must be one of the\n"
        "        available agents listed above.\n"
        "    instruction (str): A clear, detailed instruction describing the task\n"
        "        the agent should perform.\n"
        "    session_id (str): Optional session ID to continue a previous agent\n"
        "        conversation. Leave empty to start a new agent session.\n"
        "\n"
        "Returns:\n"
        "    str: The agent's response including its Session ID for continuation."
    )

    # ------------------------------------------------------------------
    # Build the function itself
    # ------------------------------------------------------------------
    # We define the function inside the factory so each call produces a
    # *new* function object (important for cache invalidation keyed on
    # ``id(func)``).
    # ------------------------------------------------------------------

    def agent(agent: str, instruction: str, session_id: str = "") -> str:
        # Placeholder implementation.
        # The actual execution is handled by AgentExecutionService which is
        # wired in Step 7 (tool_aware_renderer routes ``agent`` tool calls
        # to the execution service).  Until that wiring is in place this
        # stub returns a helpful message so development can proceed
        # incrementally.
        return (
            f"[agent tool stub] agent={agent}, instruction={instruction}, "
            f"session_id={session_id or '(new)'}"
        )

    # Attach the dynamic docstring
    agent.__doc__ = docstring
    agent.__name__ = "agent"
    agent.__qualname__ = "agent"

    return agent


def get_enabled_agent_definitions(
    agent_names: list[str],
    all_definitions: Dict[str, AgentDefinition],
) -> Dict[str, AgentDefinition]:
    """
    Filter discovered agent definitions to only those that are enabled.

    Args:
        agent_names: List of agent names currently enabled in the session.
        all_definitions: All discovered agent definitions (valid and invalid).

    Returns:
        Dict of agent name → AgentDefinition for valid, enabled agents.
    """
    enabled: Dict[str, AgentDefinition] = {}
    for name in agent_names:
        defn = all_definitions.get(name)
        if defn is None:
            logger.warning("Enabled agent '%s' not found in discovered agents", name)
            continue
        if not defn.valid:
            logger.warning(
                "Enabled agent '%s' is invalid: %s", name, defn.error_message
            )
            continue
        enabled[name] = defn
    return enabled


def build_agent_tool_for_session(
    enabled_agent_names: list[str],
    all_definitions: Optional[Dict[str, AgentDefinition]] = None,
) -> Optional[object]:
    """
    Convenience helper: discover enabled agents and return the tool callable,
    or ``None`` if no valid agents are enabled.

    This is the main entry-point used by ``ChatController._prepare_tool_context``.

    Args:
        enabled_agent_names: Names of agents enabled in the current session.
        all_definitions: Pre-discovered agent definitions.  If ``None`` a fresh
            discovery is performed.

    Returns:
        The ``agent`` tool callable, or ``None`` when nothing to expose.
    """
    if not enabled_agent_names:
        return None

    if all_definitions is None:
        from .discovery_service import AgentDiscoveryService

        discovery = AgentDiscoveryService()
        all_definitions = discovery.discover_agents()

    enabled = get_enabled_agent_definitions(enabled_agent_names, all_definitions)
    if not enabled:
        return None

    return create_agent_tool(enabled)
