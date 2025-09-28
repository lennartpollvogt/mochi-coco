# Custom Tools User Guide

## Quick Start

1. Create a `./tools` directory in your project
2. Add an `__init__.py` file with your tool functions or place the tool function in a separate file
3. Export functions in `__all__` variable
4. Start mochi-coco and a chat session
5. Type in /menu and submit to open the chat menu (shortcut: `/5`)
6. Select the option to enable tools
7. Select tools or a tool group
8. Return to chat session

## Writing Tools

### Basic Tool Structure

```python
def my_tool(param1: str, param2: int = 10) -> str:
    """
    Tool description (required).

    Args:
        param1: Description of param1
        param2: Description of param2 (optional with default)

    Returns:
        str: Description of return value
    """
    return f"Result: {param1} with {param2}"

__all__ = ['my_tool']
```

### Requirements

1. **Function Signature**: Use type hints for all parameters and return values
2. **Docstring**: Must include comprehensive description with Args and Returns sections
3. **Export**: Include function name in `__all__` list
4. **Error Handling**: Handle errors gracefully and return meaningful messages

### Best Practices

#### 1. Always Include Docstrings
The LLM uses docstrings to understand your tools. Include:
- Brief description of what the tool does
- `Args:` section with parameter descriptions
- `Returns:` section with return value description

```python
def calculate_tip(bill_amount: float, tip_percentage: float = 15.0) -> str:
    """
    Calculate tip amount and total bill.

    Args:
        bill_amount: The original bill amount in dollars
        tip_percentage: Tip percentage (default: 15%)

    Returns:
        str: Formatted string with tip amount and total
    """
    tip = bill_amount * (tip_percentage / 100)
    total = bill_amount + tip
    return f"Tip: ${tip:.2f}, Total: ${total:.2f}"
```

#### 2. Use Type Hints
Type hints help with validation and schema generation:

```python
from typing import List, Dict, Optional, Literal

def process_data(
    items: List[str],
    operation: Literal["sort", "reverse", "shuffle"],
    case_sensitive: bool = True
) -> List[str]:
    """Process a list of items with the specified operation."""
    # Implementation here
    pass
```

#### 3. Return Strings When Possible
LLMs work best with string outputs. Convert complex data to formatted strings:

```python
def analyze_text(text: str) -> str:
    """Analyze text and return statistics."""
    words = text.split()
    chars = len(text)
    lines = len(text.splitlines())

    return f"""Text Analysis:
- Words: {len(words)}
- Characters: {chars}
- Lines: {lines}
- Average word length: {chars / len(words):.1f}"""
```

#### 4. Handle Errors Gracefully
Return error messages rather than raising exceptions:

```python
def divide_numbers(a: float, b: float) -> str:
    """Divide two numbers safely."""
    try:
        if b == 0:
            return "Error: Division by zero is not allowed"
        result = a / b
        return f"{a} ÷ {b} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"
```

#### 5. Keep Tools Focused
Each tool should do one thing well:

```python
# Good - focused tool
def convert_celsius_to_fahrenheit(celsius: float) -> str:
    """Convert Celsius to Fahrenheit."""
    fahrenheit = (celsius * 9/5) + 32
    return f"{celsius}°C = {fahrenheit}°F"

# Avoid - too many responsibilities
def temperature_converter(temp: float, from_unit: str, to_unit: str,
                         also_show_kelvin: bool = False,
                         round_digits: int = 2) -> str:
    """Convert between any temperature units with options."""
    # Too complex for a single tool
    pass
```

### Tool Groups

Organize related tools into groups for easier selection:

```python
def add(a: float, b: float) -> str:
    """Add two numbers."""
    return str(a + b)

def subtract(a: float, b: float) -> str:
    """Subtract two numbers."""
    return str(a - b)

def multiply(a: float, b: float) -> str:
    """Multiply two numbers."""
    return str(a * b)

def divide(a: float, b: float) -> str:
    """Divide two numbers."""
    if b == 0:
        return "Error: Division by zero"
    return str(a / b)

# Export individual tools
__all__ = ['add', 'subtract', 'multiply', 'divide', 'uppercase', 'lowercase']

# Define groups
__math__ = ['add', 'subtract', 'multiply', 'divide']
__text__ = ['uppercase', 'lowercase']
__basic_math__ = ['add', 'subtract']
```

### Advanced Examples

#### File Operations Tool
```python
def read_file_safely(filepath: str, max_lines: int = 100) -> str:
    """
    Read file content with safety limits.

    Args:
        filepath: Path to the file to read
        max_lines: Maximum number of lines to read

    Returns:
        str: File content or error message
    """
    from pathlib import Path

    try:
        path = Path(filepath)
        if not path.exists():
            return f"Error: File '{filepath}' does not exist"

        if not path.is_file():
            return f"Error: '{filepath}' is not a file"

        with open(path, 'r', encoding='utf-8') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"... (truncated after {max_lines} lines)")
                    break
                lines.append(line.rstrip())

        return '\n'.join(lines) if lines else "(empty file)"

    except UnicodeDecodeError:
        return f"Error: Cannot read '{filepath}' - file appears to be binary"
    except Exception as e:
        return f"Error reading file: {str(e)}"
```

#### API Integration Tool
```python
def get_weather(city: str) -> str:
    """
    Get weather information for a city (mock implementation).

    Args:
        city: Name of the city

    Returns:
        str: Weather information
    """
    # This is a mock implementation - replace with real API
    import random

    if not city.strip():
        return "Error: City name cannot be empty"

    # Mock weather data
    conditions = ["sunny", "cloudy", "rainy", "snowy"]
    temps = list(range(-10, 35))

    condition = random.choice(conditions)
    temp = random.choice(temps)

    return f"Weather in {city.title()}: {condition.title()}, {temp}°C"
```

## Using Tools in Chat

### Initial Setup

1. **Start mochi-coco**: Run your chat application
2. **Select Model**: Choose a model that supports tools (indicated with "Tools: Yes")
3. **Tool Selection**: When prompted, select individual tools or tool groups
4. **Chat**: Start using the tools by asking the AI to perform relevant tasks

### Tool Selection Menu

When a tool-capable model is selected, you'll see:

```
╭─ 🛠️ Available Tools ─────────────────────────────────────────────╮
│  Single tools                                                    │
│ ╭─────┬───────────────────┬──────────────────────────────────╮     │
│ │ #   │ Tool Name         │ Tool Description                 │     │
│ ├─────┼───────────────────┼──────────────────────────────────┤     │
│ │ 1   │ calculate         │ Evaluate mathematical expression │     │
│ │ 2   │ get_weather       │ Get weather for a city           │     │
│ │ 3   │ read_file         │ Read contents of a file          │     │
│ ╰─────┴───────────────────┴──────────────────────────────────╯     │
│                                                                    │
│  Tool groups                                                       │
│ ╭─────┬───────────────────┬──────────────────────────────────╮     │
│ │ #   │ Tool Group        │ Tools Included                   │     │
│ ├─────┼───────────────────┼──────────────────────────────────┤     │
│ │ a   │ math              │ calculate, convert_temperature   │     │
│ │ b   │ system            │ read_file, list_directory        │     │
│ ╰─────┴───────────────────┴──────────────────────────────────╯     │
╰────────────────────────────────────────────────────────────────────╯
```

**Selection Options:**
- **Individual Tools**: `1,3` (select tools 1 and 3)
- **Tool Group**: `a` (select group 'a')
- **No Tools**: `none`
- **Quit**: `q`

### In-Chat Commands

#### Basic Commands
- `/menu` - Open chat menu
- `/tools` - Change tool selection
- `/tools reload` - Reload tools after making changes
- `/tools init` - Create example tools file

#### Tool Management
- `/5` or `/policy` - Toggle tool execution policy
- `/6` or `/tools` - Change selected tools

### Tool Execution Policies

Control how tools are executed:

1. **Always Confirm** - Ask before every tool execution
2. **Never Confirm** - Execute tools automatically
3. **Confirm Destructive** - Only confirm potentially dangerous operations (future)

### Tool Execution Flow

When the AI requests to use a tool:

#### With Confirmation Enabled:
```
🔧 AI requesting tool: flip_coin
╭─ 🤖 AI Tool Request ─╮
│                      │
│  Tool: flip_coin     │
│                      │
│  No arguments        │
│                      │
╰──────────────────────╯

⚠️  Allow execution? y/N: y
✓ Tool execution approved

╭──────────────────────────────╮
│ ✓ Tool 'flip_coin' completed │
│                              │
│ Output:                      │
│ Coin flip result: Tails      │
╰──────────────────────────────╯
```

#### With Confirmation Disabled:
```
🔧 AI requesting tool: flip_coin
╭──────────────────────────────╮
│ ✓ Tool 'flip_coin' completed │
│                              │
│ Output:                      │
│ Coin flip result: Tails      │
╰──────────────────────────────╯
```

## Security Considerations

### Safe Tool Design

1. **Input Validation**: Always validate inputs
2. **Path Restrictions**: Limit file access to safe directories
3. **Command Restrictions**: Only allow safe system commands
4. **Size Limits**: Limit file reading and processing sizes
5. **Timeout Protection**: Implement timeouts for long-running operations

### Example Safe File Tool

```python
def read_project_file(filename: str) -> str:
    """
    Read a file from the current project directory safely.

    Args:
        filename: Name of file to read (no path traversal allowed)

    Returns:
        str: File content or error message
    """
    from pathlib import Path
    import os

    # Security: prevent path traversal
    if '..' in filename or filename.startswith('/'):
        return "Error: Invalid filename - path traversal not allowed"

    # Security: limit to current directory and subdirectories
    try:
        filepath = Path.cwd() / filename
        filepath = filepath.resolve()

        # Ensure file is within current directory
        if not str(filepath).startswith(str(Path.cwd().resolve())):
            return "Error: File access outside project directory not allowed"

        if not filepath.exists():
            return f"Error: File '{filename}' not found"

        # Security: limit file size
        if filepath.stat().st_size > 1024 * 1024:  # 1MB limit
            return "Error: File too large (max 1MB)"

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        return content

    except Exception as e:
        return f"Error: {str(e)}"
```

### Getting Help

- Check the example tools in `tools/` within the repository
- Review error messages carefully
- Test tools with simple inputs first
- Verify your Python environment and dependencies
