"""
Agents module for mochi-coco.

This module provides functionality for discovering, configuring, and executing
LLM agents that can be invoked as tools during conversations.

Note: ``AgentExecutionService`` and prompt loaders are imported lazily to
avoid circular imports (chat.session → agents.config → agents → execution_service → chat.session).
"""

from .agent_tool import (
    build_agent_tool_for_session,
    create_agent_tool,
    get_enabled_agent_definitions,
)
from .config import AgentSettings
from .discovery_service import AgentDiscoveryService


def __getattr__(name: str):
    """Lazy imports for modules that depend on chat.session to break circular imports."""
    if name == "AgentExecutionService":
        from .execution_service import AgentExecutionService

        return AgentExecutionService
    if name == "load_planning_prompt":
        from .prompt_loader import load_planning_prompt

        return load_planning_prompt
    if name == "load_execution_prompt":
        from .prompt_loader import load_execution_prompt

        return load_execution_prompt
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AgentDiscoveryService",
    "AgentExecutionService",
    "AgentSettings",
    "build_agent_tool_for_session",
    "create_agent_tool",
    "get_enabled_agent_definitions",
    "load_execution_prompt",
    "load_planning_prompt",
]
