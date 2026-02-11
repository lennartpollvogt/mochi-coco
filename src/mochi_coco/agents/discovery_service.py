"""
Agent discovery service for finding and loading agent definitions.

This service scans the ./agents directory for agent folders, parses SKILL.md,
and loads tool functions from each agent module. It does not support tool groups.
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AgentDefinition:
    """Definition for a discovered agent."""

    name: str
    description: str
    system_prompt: str
    model: Optional[str]
    tools: Dict[str, Callable]
    valid: bool
    error_message: Optional[str] = None


class AgentDiscoveryService:
    """Service for discovering and loading agent definitions."""

    DEFAULT_AGENTS_DIR = "./agents"

    def __init__(self, agents_dir: Optional[str] = None):
        self.agents_dir = (
            Path(agents_dir) if agents_dir else Path(self.DEFAULT_AGENTS_DIR)
        )
        self._cached_definitions: Dict[str, AgentDefinition] = {}
        self._loaded = False

    def discover_agents(self) -> Dict[str, AgentDefinition]:
        """
        Discover agents from the agents directory.

        Returns:
            Dictionary mapping agent names to AgentDefinition objects.
        """
        if self._loaded and self._cached_definitions:
            return self._cached_definitions

        self._cached_definitions.clear()
        self._loaded = False

        if not self.agents_dir.exists():
            logger.info("Agents directory does not exist; discovery skipped")
            return {}

        for agent_dir in sorted(self.agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            agent_name = agent_dir.name
            # Skip special directories
            if agent_name.startswith("_") or agent_name.startswith("."):
                continue
            definition = self._discover_agent(agent_name, agent_dir)
            if definition:
                self._cached_definitions[agent_name] = definition

        self._loaded = True
        return self._cached_definitions

    def reload_agents(self) -> Dict[str, AgentDefinition]:
        """Force reload of agent definitions."""
        self._cached_definitions.clear()
        self._loaded = False

        # Remove cached modules for agent tools
        modules_to_remove = [k for k in sys.modules.keys() if k.startswith("agents.")]
        for module_name in modules_to_remove:
            del sys.modules[module_name]

        return self.discover_agents()

    def _discover_agent(
        self, agent_name: str, agent_dir: Path
    ) -> Optional[AgentDefinition]:
        """Discover a single agent from its directory."""
        skill_path = agent_dir / "SKILL.md"
        init_path = agent_dir / "__init__.py"
        module_path = agent_dir / f"{agent_name}.py"

        # Validate required files
        if not skill_path.exists():
            logger.warning("Agent '%s' missing SKILL.md", agent_name)
            return AgentDefinition(
                name=agent_name,
                description="",
                system_prompt="",
                model=None,
                tools={},
                valid=False,
                error_message="Missing SKILL.md",
            )
        if not init_path.exists():
            logger.warning("Agent '%s' missing __init__.py", agent_name)
            return AgentDefinition(
                name=agent_name,
                description="",
                system_prompt="",
                model=None,
                tools={},
                valid=False,
                error_message="Missing __init__.py",
            )
        if not module_path.exists():
            logger.warning("Agent '%s' missing %s.py", agent_name, agent_name)
            return AgentDefinition(
                name=agent_name,
                description="",
                system_prompt="",
                model=None,
                tools={},
                valid=False,
                error_message=f"Missing {agent_name}.py",
            )

        # Parse SKILL.md
        try:
            description, model, system_prompt = self._parse_skill_file(skill_path)
        except ValueError as e:
            logger.warning("Agent '%s' SKILL.md invalid: %s", agent_name, e)
            return AgentDefinition(
                name=agent_name,
                description="",
                system_prompt="",
                model=None,
                tools={},
                valid=False,
                error_message=str(e),
            )

        # Load tools from agent __init__.py (no groups)
        tools = self._load_agent_tools(agent_name, agent_dir)
        if not tools:
            return AgentDefinition(
                name=agent_name,
                description=description,
                system_prompt=system_prompt,
                model=model,
                tools={},
                valid=False,
                error_message="No valid tools found in __all__",
            )

        return AgentDefinition(
            name=agent_name,
            description=description,
            system_prompt=system_prompt,
            model=model,
            tools=tools,
            valid=True,
            error_message=None,
        )

    def _parse_skill_file(self, skill_path: Path) -> Tuple[str, Optional[str], str]:
        """
        Parse SKILL.md frontmatter and system prompt.

        Returns:
            (description, model, system_prompt)

        Raises:
            ValueError: if frontmatter is missing or malformed.
        """
        content = skill_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        if not lines or lines[0].strip() != "---":
            raise ValueError("SKILL.md missing frontmatter")

        # Parse frontmatter block
        frontmatter_lines: List[str] = []
        end_index = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break
            frontmatter_lines.append(lines[i])

        if end_index is None:
            raise ValueError("SKILL.md frontmatter not terminated")

        frontmatter = self._parse_frontmatter(frontmatter_lines)

        description = frontmatter.get("description", "").strip()
        model = frontmatter.get("model")
        if model is not None:
            model = model.strip() or None

        # System prompt is everything after the frontmatter
        system_prompt = "\n".join(lines[end_index + 1 :]).strip()

        return description, model, system_prompt

    def _parse_frontmatter(self, lines: List[str]) -> Dict[str, str]:
        """
        Parse a simple YAML-like frontmatter block.

        Supports key: value pairs only.
        """
        data: Dict[str, str] = {}
        for line in lines:
            if not line.strip() or line.strip().startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"Invalid frontmatter line: {line}")
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
        return data

    def _load_agent_tools(
        self, agent_name: str, agent_dir: Path
    ) -> Dict[str, Callable]:
        """Load tool callables from the agent's __init__.py."""
        try:
            # Load the __init__.py directly using a unique module name
            module = self._load_module(
                module_name=f"_mochi_agent_{agent_name}",
                module_path=agent_dir / "__init__.py",
            )
            if not module:
                return {}

            tools: Dict[str, Callable] = {}
            if hasattr(module, "__all__"):
                for tool_name in module.__all__:
                    if hasattr(module, tool_name):
                        func = getattr(module, tool_name)
                        if callable(func) and self._validate_tool_function(func):
                            tools[tool_name] = func
                        else:
                            logger.warning(
                                "Agent '%s' tool '%s' invalid or not callable",
                                agent_name,
                                tool_name,
                            )
            return tools
        except Exception as e:
            logger.error("Failed to load agent '%s' tools: %s", agent_name, e)
            return {}

    def _load_module(self, module_name: str, module_path: Path) -> Optional[object]:
        """Load a module from a file path."""
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if not spec or not spec.loader:
            logger.error("Failed to create module spec for %s", module_name)
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _validate_tool_function(self, func: Callable) -> bool:
        """Validate that a function meets tool requirements."""
        if not inspect.getdoc(func):
            logger.warning("Function %s has no docstring", func.__name__)
            return False

        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                logger.debug(
                    "Function %s parameter %s missing type hint",
                    func.__name__,
                    param_name,
                )

        return True
