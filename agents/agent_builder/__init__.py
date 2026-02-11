"""
Agent builder tools exports.

This module exports all tools available to the agent_builder agent.
"""

import importlib.util
import sys
from pathlib import Path

# Get the directory where this __init__.py is located
_current_dir = Path(__file__).parent

# Load the agent_builder module directly
_spec = importlib.util.spec_from_file_location(
    "_agent_builder_tools", _current_dir / "agent_builder.py"
)
if _spec and _spec.loader:
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)

    # Extract the functions we want to export
    read_file = _module.read_file
    write_file = _module.write_file
    insert_replace_text = _module.insert_replace_text
    list_dir = _module.list_dir
    delete_rename_file = _module.delete_rename_file

__all__ = [
    "read_file",
    "write_file",
    "insert_replace_text",
    "list_dir",
    "delete_rename_file",
]
