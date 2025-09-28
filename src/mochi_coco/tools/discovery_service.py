"""
Tool discovery service for finding and loading user-defined tools.

This service scans the ./tools directory for Python functions that can be used
as tools by LLMs. It supports both individual tool discovery and tool groups
as defined in the tools/__init__.py file.
"""

from typing import Dict, List, Tuple, Callable, Optional
import sys
import importlib.util
import inspect
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ToolDiscoveryService:
    """Service for discovering and loading user-defined tools."""

    DEFAULT_TOOLS_DIR = "./tools"

    def __init__(self, tools_dir: Optional[str] = None):
        self.tools_dir = Path(tools_dir) if tools_dir else Path(self.DEFAULT_TOOLS_DIR)
        self.available_functions: Dict[str, Callable] = {}
        self.tool_groups: Dict[str, List[str]] = {}
        self._module_loaded = False

    def discover_tools(self) -> Tuple[Dict[str, Callable], Dict[str, List[str]]]:
        """
        Discover tools from the tools directory.

        Returns:
            Tuple of (individual_tools, tool_groups)
        """
        # Return cached results if already loaded
        if self._module_loaded and self.available_functions:
            return self.available_functions, self.tool_groups

        # Clear previous discoveries
        self.available_functions.clear()
        self.tool_groups.clear()

        if not self.tools_dir.exists():
            logger.info(f"Tools directory {self.tools_dir} does not exist, creating it")
            self.tools_dir.mkdir(parents=True, exist_ok=True)

        init_file = self.tools_dir / "__init__.py"
        if not init_file.exists():
            logger.info(
                f"No __init__.py found in {self.tools_dir}, creating empty tools directory"
            )
            init_file.write_text("# User-defined tools\n__all__ = []\n")
            return {}, {}

        module = self._load_tools_module()
        if module:
            self.available_functions, self.tool_groups = (
                self._extract_tools_from_module(module)
            )
            self._module_loaded = True

        return self.available_functions, self.tool_groups

    def reload_tools(self) -> Tuple[Dict[str, Callable], Dict[str, List[str]]]:
        """Force reload of tools module (useful for development)."""
        # Clear cached results to force re-discovery
        self.available_functions.clear()
        self.tool_groups.clear()
        self._module_loaded = False

        # Force reload by removing cached bytecode
        pycache_dir = self.tools_dir / "__pycache__"
        if pycache_dir.exists():
            import shutil

            shutil.rmtree(pycache_dir)

        # Remove from sys.modules to force reload
        modules_to_remove = [
            k for k in sys.modules.keys() if k == "tools" or k.startswith("tools.")
        ]
        for module_name in modules_to_remove:
            del sys.modules[module_name]

        return self.discover_tools()

    def _load_tools_module(self) -> Optional[object]:
        """Load the tools module from __init__.py"""
        try:
            # Add tools directory to path temporarily
            sys.path.insert(0, str(self.tools_dir.parent))

            spec = importlib.util.spec_from_file_location(
                "tools", self.tools_dir / "__init__.py"
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
            else:
                logger.error("Failed to create module spec")
                return None

        except Exception as e:
            logger.error(f"Failed to load tools module: {e}")
            return None
        finally:
            # Clean up path
            if str(self.tools_dir.parent) in sys.path:
                sys.path.remove(str(self.tools_dir.parent))

    def _extract_tools_from_module(
        self, module
    ) -> Tuple[Dict[str, Callable], Dict[str, List[str]]]:
        """Extract tools and groups from the loaded module"""
        individual_tools = {}
        tool_groups = {}

        # Extract individual tools from __all__
        if hasattr(module, "__all__"):
            for tool_name in module.__all__:
                if hasattr(module, tool_name):
                    func = getattr(module, tool_name)
                    if callable(func) and self._validate_tool_function(func):
                        individual_tools[tool_name] = func
                    else:
                        logger.warning(f"Tool {tool_name} is not callable or invalid")

        # Extract tool groups (variables with __name__ pattern)
        for attr_name in dir(module):
            if (
                attr_name.startswith("__")
                and attr_name.endswith("__")
                and attr_name
                not in [
                    "__all__",
                    "__doc__",
                    "__file__",
                    "__name__",
                    "__package__",
                    "__builtins__",
                    "__cached__",
                    "__loader__",
                    "__spec__",
                    "__path__",
                ]
            ):
                group_name = attr_name.strip("_")
                tool_list = getattr(module, attr_name)
                if isinstance(tool_list, list):
                    # Validate that all tools in group exist
                    valid_tools = []
                    for tool_name in tool_list:
                        if tool_name in individual_tools:
                            valid_tools.append(tool_name)
                        else:
                            logger.warning(
                                f"Tool {tool_name} in group {group_name} not found in __all__"
                            )
                    if valid_tools:
                        tool_groups[group_name] = valid_tools

        return individual_tools, tool_groups

    def _validate_tool_function(self, func: Callable) -> bool:
        """Validate that a function meets tool requirements"""
        # Check for docstring
        if not inspect.getdoc(func):
            logger.warning(f"Function {func.__name__} has no docstring")
            return False

        # Check for type hints (warning only, not required)
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                logger.debug(
                    f"Function {func.__name__} parameter {param_name} missing type hint"
                )

        return True
