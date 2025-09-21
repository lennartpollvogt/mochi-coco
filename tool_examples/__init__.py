"""
Example tools collection for mochi-coco.

This file demonstrates various tool patterns and best practices.
"""

import json
import random
import os
import subprocess
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path


# === Utility Tools ===

def get_current_datetime(timezone_str: str = "UTC") -> str:
    """
    Get the current date and time.

    Args:
        timezone_str: Timezone name (currently only UTC supported)

    Returns:
        str: Current datetime in ISO format
    """
    if timezone_str.upper() == "UTC":
        return datetime.now(timezone.utc).isoformat()
    else:
        # For simplicity, return UTC with note
        return f"{datetime.now(timezone.utc).isoformat()} (UTC - {timezone_str} not supported)"


def generate_random_number(min_val: int = 1, max_val: int = 100) -> int:
    """
    Generate a random integer within a range.

    Args:
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)

    Returns:
        int: Random integer
    """
    return random.randint(min_val, max_val)


def generate_uuid() -> str:
    """
    Generate a random UUID string.

    Returns:
        str: Random UUID
    """
    import uuid
    return str(uuid.uuid4())


# === Text Processing Tools ===

def count_words(text: str) -> Dict[str, int]:
    """
    Count words and characters in text.

    Args:
        text: Text to analyze

    Returns:
        dict: Statistics about the text
    """
    words = text.split()
    return {
        "word_count": len(words),
        "character_count": len(text),
        "character_count_no_spaces": len(text.replace(" ", "")),
        "line_count": len(text.splitlines()),
        "paragraph_count": len([p for p in text.split('\n\n') if p.strip()])
    }


def reverse_text(text: str) -> str:
    """
    Reverse the given text.

    Args:
        text: Text to reverse

    Returns:
        str: Reversed text
    """
    return text[::-1]


def transform_text(text: str, operation: Literal["upper", "lower", "title", "capitalize"]) -> str:
    """
    Transform text using various operations.

    Args:
        text: Text to transform
        operation: Type of transformation to apply

    Returns:
        str: Transformed text
    """
    if operation == "upper":
        return text.upper()
    elif operation == "lower":
        return text.lower()
    elif operation == "title":
        return text.title()
    elif operation == "capitalize":
        return text.capitalize()
    else:
        raise ValueError(f"Unknown operation: {operation}")


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text using simple pattern matching.

    Args:
        text: Text to search for URLs

    Returns:
        list: List of found URLs
    """
    import re
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


# === Math Tools ===

def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.

    Args:
        expression: Mathematical expression (e.g., "2 + 2 * 3")

    Returns:
        str: Result of the calculation or error message
    """
    # Safe evaluation - only allow certain operations
    allowed_names = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'pow': pow,
        'sqrt': lambda x: x ** 0.5,
    }

    # Only allow basic math operations and functions
    allowed_chars = set('0123456789+-*/()., abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_')
    if not all(c in allowed_chars for c in expression):
        return f"Error: Invalid characters in expression: {expression}"

    try:
        # Use compile and eval for safer evaluation
        code = compile(expression, '<string>', 'eval')
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error: Could not evaluate expression: {e}"


def convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert temperature between Celsius, Fahrenheit, and Kelvin.

    Args:
        value: Temperature value
        from_unit: Source unit (C, F, or K)
        to_unit: Target unit (C, F, or K)

    Returns:
        str: Converted temperature with units
    """
    from_unit = from_unit.upper()
    to_unit = to_unit.upper()

    try:
        # Convert to Celsius first
        if from_unit == 'C':
            celsius = value
        elif from_unit == 'F':
            celsius = (value - 32) * 5/9
        elif from_unit == 'K':
            celsius = value - 273.15
        else:
            return f"Error: Unknown source unit: {from_unit}"

        # Convert from Celsius to target
        if to_unit == 'C':
            result = celsius
        elif to_unit == 'F':
            result = celsius * 9/5 + 32
        elif to_unit == 'K':
            result = celsius + 273.15
        else:
            return f"Error: Unknown target unit: {to_unit}"

        return f"{result:.2f}°{to_unit}"
    except Exception as e:
        return f"Error: {e}"


def calculate_percentage(part: float, whole: float) -> str:
    """
    Calculate what percentage one number is of another.

    Args:
        part: The part value
        whole: The whole value

    Returns:
        str: Percentage with formatting
    """
    try:
        if whole == 0:
            return "Error: Cannot calculate percentage with zero as whole"
        percentage = (part / whole) * 100
        return f"{percentage:.2f}%"
    except Exception as e:
        return f"Error: {e}"


# === JSON Tools ===

def parse_json(json_string: str) -> str:
    """
    Parse a JSON string and return formatted result.

    Args:
        json_string: JSON string to parse

    Returns:
        str: Parsed and formatted JSON or error message
    """
    try:
        data = json.loads(json_string)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {e}"
    except Exception as e:
        return f"Error: {e}"


def format_json(data_string: str, indent: int = 2) -> str:
    """
    Format a JSON string with proper indentation.

    Args:
        data_string: JSON string to format
        indent: Number of spaces for indentation

    Returns:
        str: Formatted JSON string or error message
    """
    try:
        data = json.loads(data_string)
        return json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=True)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {e}"
    except Exception as e:
        return f"Error: {e}"


def extract_json_value(json_string: str, key_path: str) -> str:
    """
    Extract a value from JSON using dot notation key path.

    Args:
        json_string: JSON string to parse
        key_path: Dot-separated key path (e.g., "user.profile.name")

    Returns:
        str: Extracted value or error message
    """
    try:
        data = json.loads(json_string)
        keys = key_path.split('.')

        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                index = int(key)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return f"Error: List index {index} out of range"
            else:
                return f"Error: Key '{key}' not found"

        return str(current)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {e}"
    except Exception as e:
        return f"Error: {e}"


# === File System Tools ===

def list_directory_contents(path: str = ".") -> str:
    """
    List contents of a directory.

    Args:
        path: Directory path to list (defaults to current directory)

    Returns:
        str: Directory listing or error message
    """
    try:
        directory = Path(path)
        if not directory.exists():
            return f"Error: Directory '{path}' does not exist"

        if not directory.is_dir():
            return f"Error: '{path}' is not a directory"

        contents = []
        for item in sorted(directory.iterdir()):
            item_type = "📁" if item.is_dir() else "📄"
            size = ""
            if item.is_file():
                try:
                    size = f" ({item.stat().st_size} bytes)"
                except:
                    size = ""
            contents.append(f"{item_type} {item.name}{size}")

        if not contents:
            return f"Directory '{path}' is empty"

        return f"Contents of '{path}':\n" + "\n".join(contents)
    except Exception as e:
        return f"Error: {e}"


def get_file_info(filepath: str) -> str:
    """
    Get information about a file.

    Args:
        filepath: Path to the file

    Returns:
        str: File information or error message
    """
    try:
        file_path = Path(filepath)
        if not file_path.exists():
            return f"Error: File '{filepath}' does not exist"

        stat = file_path.stat()
        info = []
        info.append(f"File: {file_path.name}")
        info.append(f"Path: {file_path.absolute()}")
        info.append(f"Size: {stat.st_size} bytes")
        info.append(f"Type: {'Directory' if file_path.is_dir() else 'File'}")

        # Convert timestamp to readable format
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        info.append(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(info)
    except Exception as e:
        return f"Error: {e}"


def read_file_content(filepath: str, max_lines: int = 50) -> str:
    """
    Read and return file content with line limit.

    Args:
        filepath: Path to the file to read
        max_lines: Maximum number of lines to read

    Returns:
        str: File content or error message
    """
    try:
        file_path = Path(filepath)
        if not file_path.exists():
            return f"Error: File '{filepath}' does not exist"

        if not file_path.is_file():
            return f"Error: '{filepath}' is not a file"

        # Try to read as text
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... (truncated after {max_lines} lines)")
                        break
                    lines.append(line.rstrip())

                return "\n".join(lines) if lines else "(empty file)"
        except UnicodeDecodeError:
            return f"Error: File '{filepath}' is not a text file (binary content)"
    except Exception as e:
        return f"Error: {e}"


# === System Tools ===

def get_current_working_directory() -> str:
    """
    Get the current working directory.

    Returns:
        str: Current working directory path
    """
    return str(Path.cwd())


def run_command(command: str, shell: bool = True) -> str:
    """
    Run a system command safely (limited to safe commands).

    Args:
        command: Command to run
        shell: Whether to run in shell mode

    Returns:
        str: Command output or error message
    """
    # List of safe commands (extend as needed)
    safe_commands = {
        'ls', 'dir', 'pwd', 'date', 'whoami', 'uname', 'uptime',
        'echo', 'cat', 'head', 'tail', 'wc', 'grep', 'find',
        'git status', 'git log --oneline -10', 'git branch',
        'python --version', 'python3 --version', 'pip --version',
        'node --version', 'npm --version'
    }

    # Extract the base command
    base_command = command.split()[0] if command.split() else ""

    # Check if it's a safe command or starts with a safe prefix
    is_safe = (
        command in safe_commands or
        any(command.startswith(safe_cmd) for safe_cmd in safe_commands) or
        base_command in ['ls', 'pwd', 'date', 'whoami', 'echo', 'cat', 'head', 'tail', 'wc']
    )

    if not is_safe:
        return f"Error: Command '{command}' is not in the list of safe commands"

    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=10  # 10 second timeout
        )

        if result.returncode == 0:
            return result.stdout.strip() if result.stdout else "(no output)"
        else:
            error_msg = result.stderr.strip() if result.stderr else f"Command failed with exit code {result.returncode}"
            return f"Error: {error_msg}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 10 seconds"
    except Exception as e:
        return f"Error: {e}"


def get_environment_variable(var_name: str) -> str:
    """
    Get the value of an environment variable.

    Args:
        var_name: Name of the environment variable

    Returns:
        str: Environment variable value or indication if not set
    """
    value = os.getenv(var_name)
    if value is None:
        return f"Environment variable '{var_name}' is not set"
    return value


# === Network Tools (Mock/Safe) ===

def ping_host(hostname: str) -> str:
    """
    Simulate pinging a host (safe mock implementation).

    Args:
        hostname: Hostname or IP address to ping

    Returns:
        str: Mock ping result
    """
    # This is a mock implementation for safety
    # In a real implementation, you might use subprocess to call ping
    import random

    if not hostname:
        return "Error: Hostname cannot be empty"

    # Simulate random response times
    response_time = round(random.uniform(1, 100), 2)
    success_rate = random.choice([True, True, True, False])  # 75% success rate

    if success_rate:
        return f"PING {hostname}: time={response_time}ms (simulated)"
    else:
        return f"PING {hostname}: Request timeout (simulated)"


def check_port(hostname: str, port: int) -> str:
    """
    Check if a port is open on a host (safe mock implementation).

    Args:
        hostname: Hostname or IP address
        port: Port number to check

    Returns:
        str: Port status (mock result)
    """
    # Mock implementation for safety
    import random

    if not hostname:
        return "Error: Hostname cannot be empty"

    if not (1 <= port <= 65535):
        return "Error: Port must be between 1 and 65535"

    # Simulate port status
    is_open = random.choice([True, False])

    if is_open:
        return f"Port {port} on {hostname} is OPEN (simulated)"
    else:
        return f"Port {port} on {hostname} is CLOSED (simulated)"


# Export all tools
__all__ = [
    # Utility tools
    'get_current_datetime',
    'generate_random_number',
    'generate_uuid',
    # Text processing
    'count_words',
    'reverse_text',
    'transform_text',
    'extract_urls',
    # Math tools
    'calculate',
    'convert_temperature',
    'calculate_percentage',
    # JSON tools
    'parse_json',
    'format_json',
    'extract_json_value',
    # File system tools
    'list_directory_contents',
    'get_file_info',
    'read_file_content',
    # System tools
    'get_current_working_directory',
    'run_command',
    'get_environment_variable',
    # Network tools (mock)
    'ping_host',
    'check_port'
]

# Tool groups for organized access
__utility__ = ['get_current_datetime', 'generate_random_number', 'generate_uuid']
__text__ = ['count_words', 'reverse_text', 'transform_text', 'extract_urls']
__math__ = ['calculate', 'convert_temperature', 'calculate_percentage']
__json__ = ['parse_json', 'format_json', 'extract_json_value']
__filesystem__ = ['list_directory_contents', 'get_file_info', 'read_file_content']
__system__ = ['get_current_working_directory', 'run_command', 'get_environment_variable']
__network__ = ['ping_host', 'check_port']
__development__ = ['run_command', 'get_current_working_directory', 'read_file_content']
