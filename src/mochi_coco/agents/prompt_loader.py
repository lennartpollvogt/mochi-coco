"""
Prompt loader for agent ephemeral planning and execution prompts.

This module loads and caches the ephemeral prompt templates used during the
agent two-phase loop (planning + execution). These prompts are appended to
API requests but **never persisted** to agent chat history.

Prompt files are loaded from:
- ``docs/agents/agent_prompt_planning.md``
- ``docs/agents/agent_prompt_execution.md``
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default paths relative to the project root (cwd)
_DEFAULT_PLANNING_PROMPT_PATH = "docs/agents/agent_prompt_planning.md"
_DEFAULT_EXECUTION_PROMPT_PATH = "docs/agents/agent_prompt_execution.md"

# Module-level cache so we only read from disk once per process
_planning_prompt_cache: Optional[str] = None
_execution_prompt_cache: Optional[str] = None


def load_planning_prompt(path: Optional[str] = None) -> str:
    """
    Load the ephemeral planning prompt template.

    The prompt instructs the agent to plan without calling tools.
    It is appended as an extra ``user`` message in the API request
    but is **not** persisted to the agent chat history.

    Args:
        path: Optional override for the prompt file path.
            Defaults to ``docs/agents/agent_prompt_planning.md``.

    Returns:
        The planning prompt text.  Returns a hardcoded fallback if the
        file cannot be read.
    """
    global _planning_prompt_cache

    if _planning_prompt_cache is not None and path is None:
        return _planning_prompt_cache

    prompt = _read_prompt_file(
        path or _DEFAULT_PLANNING_PROMPT_PATH,
        fallback=_FALLBACK_PLANNING_PROMPT,
    )

    if path is None:
        _planning_prompt_cache = prompt

    return prompt


def load_execution_prompt(path: Optional[str] = None) -> str:
    """
    Load the ephemeral execution prompt template.

    The prompt instructs the agent to execute the plan using tools.
    It is appended as an extra ``user`` message in the API request
    but is **not** persisted to the agent chat history.

    Args:
        path: Optional override for the prompt file path.
            Defaults to ``docs/agents/agent_prompt_execution.md``.

    Returns:
        The execution prompt text.  Returns a hardcoded fallback if the
        file cannot be read.
    """
    global _execution_prompt_cache

    if _execution_prompt_cache is not None and path is None:
        return _execution_prompt_cache

    prompt = _read_prompt_file(
        path or _DEFAULT_EXECUTION_PROMPT_PATH,
        fallback=_FALLBACK_EXECUTION_PROMPT,
    )

    if path is None:
        _execution_prompt_cache = prompt

    return prompt


def clear_cache() -> None:
    """Clear the cached prompts so they are re-read from disk on next access."""
    global _planning_prompt_cache, _execution_prompt_cache
    _planning_prompt_cache = None
    _execution_prompt_cache = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_prompt_file(file_path: str, fallback: str) -> str:
    """
    Read a prompt file from disk.

    Args:
        file_path: Path to the prompt file (relative to cwd or absolute).
        fallback: Hardcoded fallback content if the file is missing or unreadable.

    Returns:
        The file content, or *fallback* on any error.
    """
    resolved = Path(file_path)
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved

    try:
        if not resolved.exists():
            logger.warning(
                "Prompt file '%s' not found; using built-in fallback", file_path
            )
            return fallback

        content = resolved.read_text(encoding="utf-8").strip()
        if not content:
            logger.warning(
                "Prompt file '%s' is empty; using built-in fallback", file_path
            )
            return fallback

        return content

    except Exception as e:
        logger.error(
            "Failed to read prompt file '%s': %s; using built-in fallback",
            file_path,
            e,
        )
        return fallback


# ---------------------------------------------------------------------------
# Hardcoded fallback prompts (mirrors the content in docs/agents/)
# ---------------------------------------------------------------------------

_FALLBACK_PLANNING_PROMPT = (
    "## Planning Prompt (no tools)\n"
    "\n"
    "You are in the planning phase.\n"
    "\n"
    "- Read the conversation and the instruction.\n"
    "- Think about the task, break it down, and propose a clear plan.\n"
    "- Do NOT call any tools in this step.\n"
    "- Output ONLY your plan."
)

_FALLBACK_EXECUTION_PROMPT = (
    "## Execution Prompt (tools allowed)\n"
    "\n"
    "You are now in the execution phase.\n"
    "\n"
    "- Follow the plan and perform the task.\n"
    "- Use tools only when needed.\n"
    "- If you need clarification, ask a direct, concise question.\n"
    "- If you can finish, return the final response without calling tools."
)
