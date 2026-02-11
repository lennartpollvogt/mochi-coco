"""
Coder agent tools for file system operations, code editing, and shell command execution.

This module provides a comprehensive set of tools for:
- Reading and writing files
- Editing files with precise line control
- Listing directory contents
- Deleting and renaming files
- Executing shell commands
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def read_file(file_path: str, max_lines: int | None = None) -> str:
    """
    Reads the contents of a file and returns its contents with line numbers as a string.

    Args:
        file_path (str): The path to the file to be read.
        max_lines (int | None): Maximum number of lines to read. If None, reads entire file.

    Returns:
        str: The contents of the file with line numbers.
    """
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            if max_lines is not None:
                lines = lines[:max_lines]
            return "\n".join(
                f"{i + 1}: {line.rstrip()}" for i, line in enumerate(lines)
            )
    except FileNotFoundError:
        return f"File '{file_path}' not found."
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


def write_file(file_path: str, text: str) -> str:
    """
    A function to write text into a file.
    If the file does not exist, it will be created.
    If the file already exists, it will be overwritten.
    If the directory does not exist, it will be created.

    Args:
        file_path (str): The path to the file to write.
        text (str): The text to write into the file.

    Returns:
        str: The content (with line numbers) of the file after writing.
    """
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        # Remove trailing whitespace from all lines
        lines = text.split("\n")
        lines = [line.rstrip() for line in lines]

        # Remove trailing empty lines
        while lines and lines[-1] == "":
            lines.pop()

        # Join lines and ensure file ends with a single newline if not empty
        if lines:
            cleaned_text = "\n".join(lines) + "\n"
        else:
            cleaned_text = ""

        with open(file_path, "w") as file:
            file.write(cleaned_text)

        return f"Successfully wrote to '{file_path}'.\n\n" + read_file(file_path)
    except Exception as e:
        return f"Error writing to file '{file_path}': {str(e)}"


def insert_replace_text(
    mode: str,
    file_path: str,
    start_line: int,
    end_line: int | None,
    new_text: str,
) -> str:
    """
    Insert or replace text within a file at the specified lines.

    Args:
        mode (str): The mode of operation. Must be either "insert" or "replace".
        file_path (str): The path to the file to be modified.
        start_line (int): The line number where the insertation or replacement should start.
        end_line (int | None): The line number where the insertation or replacement should end. In case of mode "insert" the end_line is ignored.
        new_text (str): The new text to insert or replace the existing text.

    Returns:
        str: The modified content of the file plus 4 leading and 4 trailing lines.
    """
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()

        # Split new_text into individual lines if it contains newlines
        new_lines = new_text.split("\n")
        # Add newline character to each line (except empty last line if text ends with \n)
        new_lines_formatted = [
            line + "\n" for line in new_lines if line or new_lines[-1] != line
        ]

        if mode == "insert":
            # Insert new text at the specified line, ignoring end_line
            for i, line in enumerate(new_lines_formatted):
                lines.insert(start_line - 1 + i, line)
        elif mode == "replace":
            # Replace text between start_line and end_line
            if end_line is None:
                end_line = start_line
            lines[start_line - 1 : end_line] = new_lines_formatted

        # Remove trailing whitespace from all lines
        lines = [line.rstrip() + "\n" for line in lines]

        # Remove trailing empty lines
        while lines and lines[-1].strip() == "":
            lines.pop()

        # Ensure file ends with a single newline if it's not empty
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"

        with open(file_path, "w") as file:
            file.writelines(lines)

        # Return modified content with 4 leading and 4 trailing lines
        total_lines = len(lines)
        context_start = max(0, start_line - 5)  # -5 because start_line is 1-indexed
        context_end = min(total_lines, start_line + 4)

        # Add line numbers to the returned text
        result_lines = []
        for i in range(context_start, context_end):
            line_number = i + 1  # Convert to 1-indexed line numbers
            line_content = lines[i].rstrip("\n")  # Remove newline for formatting
            result_lines.append(f"{line_number:4d}: {line_content}")

        return "\n".join(result_lines)
    except FileNotFoundError:
        return f"File '{file_path}' not found."
    except Exception as e:
        return f"Error editing file '{file_path}': {str(e)}"


def list_dir(directory_path: str = ".") -> str:
    """
    List files and directories in a directory.

    Args:
        directory_path (str): The path to the directory to list. Defaults to the current directory.

    Returns:
        str: A string containing the list of files and directories in the directory.
    """
    # Files and directories to exclude
    excluded_items = {
        ".DS_Store",
        "uv.lock",
        ".gitignore",
        ".venv",
        ".python-version",
        ".git",
    }

    try:
        files = Path(directory_path).iterdir()
        filtered_files = [file for file in files if file.name not in excluded_items]

        return "\n".join(f"- {file}" for file in filtered_files)
    except FileNotFoundError:
        return f"Directory '{directory_path}' not found."
    except Exception as e:
        return f"Error listing directory '{directory_path}': {str(e)}"


def delete_rename_file(file_path: str, mode: str, new_name: str | None = None) -> str:
    """
    Delete or rename a file from the filesystem based on the specified mode.

    Args:
        file_path (str): The path to the file to be deleted or renamed.
        mode (str): The operation mode. Must be either "delete" or "rename".
        new_name (str | None): The new name/path for the file. Required when mode is "rename".

    Returns:
        str: Confirmation message indicating whether the operation was successful.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the user doesn't have permission to delete/rename the file.
        OSError: If there's an error during the operation (e.g., file is in use).
    """
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist."

        # Check if it's actually a file (not a directory)
        if not os.path.isfile(file_path):
            return f"Error: '{file_path}' is not a file (it might be a directory)."

        if mode == "delete":
            # Delete the file
            os.remove(file_path)
            return f"Successfully deleted file: {file_path}"

        elif mode == "rename":
            # Check if new_name is provided
            if new_name is None:
                return "Error: new_name parameter is required when mode is 'rename'."

            # Check if new_name is not empty
            if not new_name.strip():
                return "Error: new_name cannot be empty."

            # Check if target already exists
            if os.path.exists(new_name):
                return f"Error: Target file '{new_name}' already exists."

            # Rename the file
            os.rename(file_path, new_name)
            return f"Successfully renamed file from '{file_path}' to '{new_name}'."

        else:
            return f"Error: Invalid mode '{mode}'. Must be 'delete' or 'rename'."

    except PermissionError:
        operation = "delete" if mode == "delete" else "rename"
        return f"Error: Permission denied. Cannot {operation} '{file_path}'."
    except OSError as e:
        operation = "delete" if mode == "delete" else "rename"
        return f"Error: Could not {operation} '{file_path}'. {str(e)}"
    except Exception as e:
        operation = "delete" if mode == "delete" else "rename"
        return f"Unexpected error while trying to {operation} '{file_path}': {str(e)}"


def run_cli_command(command: str) -> str:
    """Execute command in a shell and return its output.

    Parameters:
        command (str): The shell command to run.

    Returns:
        str: Standard output if the command exits with status 0; otherwise the standard error is returned.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return f"Command execution failed: {exc}"

    return result.stdout if result.returncode == 0 else result.stderr
