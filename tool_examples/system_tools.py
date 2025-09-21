"""
Example system tools for mochi-coco.

This module provides example tools for system operations that can be used
by LLMs during chat sessions. These demonstrate safe system interactions
with proper error handling and security considerations.
"""

import subprocess
import platform
import os
import shutil
from typing import Optional


def run_command(command: str, working_directory: Optional[str] = None) -> str:
    """
    Execute a shell command and return the output.

    Args:
        command (str): The command to execute
        working_directory (Optional[str]): Directory to run the command in. Defaults to current directory.

    Returns:
        str: Command output and exit code, or error message
    """
    try:
        # Security: Basic validation to prevent dangerous commands
        dangerous_patterns = ['rm -rf', 'del /f', 'format', 'mkfs', 'dd if=', '> /dev/', 'shutdown', 'reboot']
        command_lower = command.lower()

        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return f"Error: Command '{command}' contains potentially dangerous pattern '{pattern}' and was blocked for safety."

        # Change to specified directory if provided
        cwd = working_directory if working_directory else os.getcwd()

        # Execute command with timeout
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
            cwd=cwd
        )

        output_lines = []
        output_lines.append(f"Command: {command}")
        output_lines.append(f"Working Directory: {cwd}")
        output_lines.append(f"Exit Code: {result.returncode}")

        if result.stdout:
            output_lines.append(f"Output:\n{result.stdout}")

        if result.stderr:
            output_lines.append(f"Error Output:\n{result.stderr}")

        if result.returncode == 0:
            output_lines.append("✅ Command completed successfully")
        else:
            output_lines.append("❌ Command failed")

        return "\n".join(output_lines)

    except subprocess.TimeoutExpired:
        return f"Error: Command '{command}' timed out after 30 seconds."
    except FileNotFoundError:
        return f"Error: Working directory '{working_directory}' does not exist."
    except Exception as e:
        return f"Error executing command '{command}': {str(e)}"


def get_system_info() -> str:
    """
    Get information about the current system.

    Returns:
        str: System information including OS, architecture, and environment details
    """
    try:
        info = []

        # Basic system info
        info.append(f"Operating System: {platform.system()} {platform.release()}")
        info.append(f"Architecture: {platform.machine()}")
        info.append(f"Processor: {platform.processor()}")
        info.append(f"Python Version: {platform.python_version()}")
        info.append(f"Node Name: {platform.node()}")

        # Current working directory
        info.append(f"Current Directory: {os.getcwd()}")

        # Environment info
        info.append(f"User: {os.getenv('USER', 'Unknown')}")
        info.append(f"Home Directory: {os.getenv('HOME', 'Unknown')}")
        info.append(f"Shell: {os.getenv('SHELL', 'Unknown')}")

        # Disk space (if available)
        try:
            total, used, free = shutil.disk_usage('/')
            info.append(f"Disk Space - Total: {total // (1024**3)} GB, Used: {used // (1024**3)} GB, Free: {free // (1024**3)} GB")
        except:
            info.append("Disk Space: Unable to retrieve")

        return "\n".join(info)

    except Exception as e:
        return f"Error getting system information: {str(e)}"


def get_environment_variable(variable_name: str) -> str:
    """
    Get the value of an environment variable.

    Args:
        variable_name (str): Name of the environment variable to retrieve

    Returns:
        str: Value of the environment variable or indication if not found
    """
    try:
        value = os.getenv(variable_name)

        if value is None:
            return f"Environment variable '{variable_name}' is not set."

        # Don't expose potentially sensitive variables
        sensitive_vars = ['PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'CREDENTIAL']
        if any(sensitive in variable_name.upper() for sensitive in sensitive_vars):
            return f"Environment variable '{variable_name}' contains sensitive information and cannot be displayed."

        return f"{variable_name}={value}"

    except Exception as e:
        return f"Error getting environment variable '{variable_name}': {str(e)}"


def find_files(pattern: str, directory: str = ".", max_results: int = 50) -> str:
    """
    Find files matching a pattern in a directory.

    Args:
        pattern (str): File pattern to search for (supports wildcards like *.py)
        directory (str): Directory to search in. Defaults to current directory.
        max_results (int): Maximum number of results to return. Defaults to 50.

    Returns:
        str: List of matching files or error message
    """
    try:
        from pathlib import Path
        import fnmatch

        search_path = Path(directory)

        if not search_path.exists():
            return f"Error: Directory '{directory}' does not exist."

        if not search_path.is_dir():
            return f"Error: '{directory}' is not a directory."

        matches = []
        count = 0

        # Search recursively
        for file_path in search_path.rglob('*'):
            if count >= max_results:
                matches.append(f"... (truncated at {max_results} results)")
                break

            if file_path.is_file() and fnmatch.fnmatch(file_path.name, pattern):
                relative_path = file_path.relative_to(search_path)
                file_size = file_path.stat().st_size

                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"

                matches.append(f"{relative_path} ({size_str})")
                count += 1

        if not matches:
            return f"No files matching pattern '{pattern}' found in '{directory}'."

        result = f"Found {count} file(s) matching '{pattern}' in '{directory}':\n\n"
        result += "\n".join(matches)

        return result

    except PermissionError:
        return f"Error: Permission denied searching in '{directory}'."
    except Exception as e:
        return f"Error finding files with pattern '{pattern}': {str(e)}"


def get_process_info() -> str:
    """
    Get information about the current process and system load.

    Returns:
        str: Process and system information
    """
    try:
        import psutil
        import os

        info = []

        # Current process info
        current_process = psutil.Process(os.getpid())
        info.append(f"Current Process ID: {os.getpid()}")
        info.append(f"Process Name: {current_process.name()}")
        info.append(f"CPU Usage: {current_process.cpu_percent():.1f}%")
        info.append(f"Memory Usage: {current_process.memory_info().rss / (1024 * 1024):.1f} MB")

        # System info
        info.append(f"System CPU Usage: {psutil.cpu_percent(interval=1):.1f}%")
        memory = psutil.virtual_memory()
        info.append(f"System Memory Usage: {memory.percent:.1f}% ({memory.used / (1024**3):.1f} GB / {memory.total / (1024**3):.1f} GB)")

        # Load average (Unix-like systems)
        if hasattr(os, 'getloadavg'):
            load1, load5, load15 = os.getloadavg()
            info.append(f"Load Average: {load1:.2f}, {load5:.2f}, {load15:.2f}")

        return "\n".join(info)

    except ImportError:
        return "Error: psutil package not available. Install with 'pip install psutil' for process information."
    except Exception as e:
        return f"Error getting process information: {str(e)}"
