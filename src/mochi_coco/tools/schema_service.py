"""
Tool schema service for converting Python functions to Ollama tool schemas.

This service leverages Ollama's built-in utilities to convert Python functions
into Tool objects that can be passed to the LLM for function calling.
"""

from typing import Dict, Callable
from ollama import Tool
from ollama._utils import convert_function_to_tool, _parse_docstring
import inspect
import logging

logger = logging.getLogger(__name__)

class ToolSchemaService:
    """Service for converting Python functions to Ollama tool schemas."""

    def __init__(self):
        self._tool_cache: Dict[str, Tool] = {}

    def convert_functions_to_tools(self, functions: Dict[str, Callable]) -> Dict[str, Tool]:
        """
        Convert dictionary of functions to Ollama Tool objects.
        Uses caching to avoid re-conversion.

        Args:
            functions: Dictionary mapping function names to callable functions

        Returns:
            Dictionary mapping function names to Tool objects
        """
        tools = {}
        for name, func in functions.items():
            # Check cache first
            cache_key = f"{name}_{id(func)}"
            if cache_key in self._tool_cache:
                tools[name] = self._tool_cache[cache_key]
                continue

            try:
                # Use Ollama's built-in conversion
                tool = convert_function_to_tool(func)
                tools[name] = tool
                self._tool_cache[cache_key] = tool
            except Exception as e:
                logger.error(f"Failed to convert function {name} to tool: {e}")

        return tools

    def clear_cache(self):
        """Clear the tool conversion cache."""
        self._tool_cache.clear()

    def get_tool_descriptions(self, functions: Dict[str, Callable]) -> Dict[str, str]:
        """
        Extract descriptions from function docstrings for UI display.

        Uses Ollama's _parse_docstring to handle various docstring formats.

        Args:
            functions: Dictionary of function name to callable function

        Returns:
            Dictionary mapping function names to description strings
        """
        descriptions = {}
        for name, func in functions.items():
            docstring = inspect.getdoc(func)
            if docstring:
                try:
                    parsed = _parse_docstring(docstring)
                    # The main description is stored under the hash key
                    doc_hash = str(hash(docstring))
                    description = parsed.get(doc_hash, "").strip()
                    # Take first line for UI display
                    if description:
                        first_line = description.split('\n')[0].strip()
                        descriptions[name] = first_line if first_line else f"Function {name}"
                    else:
                        descriptions[name] = f"Function {name}"
                except Exception as e:
                    logger.warning(f"Failed to parse docstring for {name}: {e}")
                    descriptions[name] = f"Function {name}"
            else:
                descriptions[name] = f"Function {name}"

        return descriptions
