"""
Example tools module for mochi-coco.

This module demonstrates how to organize and export tools for use with LLMs.
Copy this directory to ./tools/ in your working directory and modify as needed.
"""

from .file_operations import read_file, write_file, list_directory, get_file_info
from .system_tools import run_command, get_system_info, get_environment_variable, find_files, get_process_info

# Individual tools available for selection
__all__ = [
    "read_file",
    "write_file",
    "list_directory",
    "get_file_info",
    "run_command",
    "get_system_info",
    "get_environment_variable",
    "find_files",
    "get_process_info"
]

# Tool groups for domain-specific functionality
__file_operations__ = ["read_file", "write_file", "list_directory", "get_file_info"]
__system_admin__ = ["run_command", "get_system_info", "get_environment_variable", "find_files", "get_process_info"]
__basic_tools__ = ["read_file", "list_directory", "get_system_info"]
__developer_tools__ = ["find_files", "run_command", "read_file", "write_file"]
