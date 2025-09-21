"""
Example file operations tools for mochi-coco.

This module provides example tools for file system operations that can be used
by LLMs during chat sessions. These demonstrate how to create well-documented
tools with proper error handling.
"""

import os
from pathlib import Path
from typing import Union


def read_file(file_path: str) -> str:
    """
    Read the contents of a file.

    Args:
        file_path (str): Path to the file to read

    Returns:
        str: Contents of the file, or error message if file cannot be read
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File '{file_path}' does not exist."

        if not path.is_file():
            return f"Error: '{file_path}' is not a file."

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        return f"Contents of '{file_path}':\n\n{content}"

    except PermissionError:
        return f"Error: Permission denied reading '{file_path}'."
    except UnicodeDecodeError:
        return f"Error: Cannot decode '{file_path}' as UTF-8 text."
    except Exception as e:
        return f"Error reading '{file_path}': {str(e)}"


def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file.

    Args:
        file_path (str): Path to the file to write
        content (str): Content to write to the file

    Returns:
        str: Success message or error description
    """
    try:
        path = Path(file_path)

        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Successfully wrote {len(content)} characters to '{file_path}'."

    except PermissionError:
        return f"Error: Permission denied writing to '{file_path}'."
    except Exception as e:
        return f"Error writing to '{file_path}': {str(e)}"


def list_directory(directory_path: str = ".") -> str:
    """
    List contents of a directory.

    Args:
        directory_path (str): Path to the directory to list. Defaults to current directory.

    Returns:
        str: Directory listing or error message
    """
    try:
        path = Path(directory_path)

        if not path.exists():
            return f"Error: Directory '{directory_path}' does not exist."

        if not path.is_dir():
            return f"Error: '{directory_path}' is not a directory."

        items = []
        for item in sorted(path.iterdir()):
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                items.append(f"📄 {item.name} ({size_str})")

        if not items:
            return f"Directory '{directory_path}' is empty."

        return f"Contents of '{directory_path}':\n\n" + "\n".join(items)

    except PermissionError:
        return f"Error: Permission denied accessing '{directory_path}'."
    except Exception as e:
        return f"Error listing '{directory_path}': {str(e)}"


def get_file_info(file_path: str) -> str:
    """
    Get information about a file or directory.

    Args:
        file_path (str): Path to the file or directory

    Returns:
        str: File information or error message
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return f"Error: '{file_path}' does not exist."

        stat = path.stat()

        # Basic info
        info = [f"Path: {path.absolute()}"]

        if path.is_file():
            info.append("Type: File")
            info.append(f"Size: {stat.st_size:,} bytes")
        elif path.is_dir():
            info.append("Type: Directory")
            try:
                item_count = len(list(path.iterdir()))
                info.append(f"Items: {item_count}")
            except PermissionError:
                info.append("Items: (permission denied)")

        # Permissions
        mode = stat.st_mode
        perms = []
        if mode & 0o400: perms.append("r")
        else: perms.append("-")
        if mode & 0o200: perms.append("w")
        else: perms.append("-")
        if mode & 0o100: perms.append("x")
        else: perms.append("-")

        info.append(f"Permissions: {''.join(perms)}")

        # Timestamps
        import time
        info.append(f"Modified: {time.ctime(stat.st_mtime)}")
        info.append(f"Created: {time.ctime(stat.st_ctime)}")

        return "\n".join(info)

    except PermissionError:
        return f"Error: Permission denied accessing '{file_path}'."
    except Exception as e:
        return f"Error getting info for '{file_path}': {str(e)}"
