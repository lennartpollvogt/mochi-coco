# Phase 4: Session Persistence & UI Polish

## 4.1 Enhanced Session Metadata
**File**: `src/mochi_coco/chat/session.py` (modifications to SessionMetadata)

```python
@dataclass
class SessionMetadata:
    session_id: str
    model: str
    created_at: str
    updated_at: str
    message_count: int = 0
    summary: Optional[Dict[str, Any]] = None
    summary_model: Optional[str] = None
    # Add version for backward compatibility
    format_version: str = "1.1"
    # Add tools settings
    tools_settings: Optional[Dict[str, Any]] = None
    
    def migrate_from_legacy(self):
        """Migrate from older session format."""
        # Handle old sessions without format_version
        if not hasattr(self, 'format_version'):
            self.format_version = "1.0"
            
        # Migrate from 1.0 to 1.1 (add tools support)
        if self.format_version == "1.0":
            if not hasattr(self, 'tools_settings'):
                self.tools_settings = None
            self.format_version = "1.1"
```

## 4.2 Enhanced Menu System
**File**: `src/mochi_coco/ui/menu_display.py` (modifications)

```python
def display_command_menu(self, has_system_prompts: bool = False, 
                        has_tools: bool = False, 
                        tool_settings: Optional[ToolSettings] = None) -> None:
    """Enhanced command menu with dynamic tool options."""
    
    commands = [
        ("1", "💬 Switch Sessions", "Change to different chat session"),
        ("2", "🤖 Change Model", "Select a different AI model"),
        ("3", "📝 Toggle Markdown", "Enable/disable markdown rendering"),
        ("4", "🤔 Toggle Thinking", "Show/hide thinking blocks")
    ]
    
    # Dynamic command numbering
    next_num = 5
    
    if has_tools:
        # Tool-related commands
        if tool_settings:
            policy_status = tool_settings.execution_policy.value.replace('_', ' ').title()
            commands.append((str(next_num), "🛠️ Tool Policy", f"Current: {policy_status}"))
            next_num += 1
            
            if tool_settings.is_enabled():
                active_count = len(tool_settings.tools) if tool_settings.tools else 0
                if tool_settings.tool_group:
                    status = f"Group: {tool_settings.tool_group}"
                else:
                    status = f"{active_count} tool(s) selected"
                commands.append((str(next_num), "📂 Change Tools", status))
            else:
                commands.append((str(next_num), "📂 Select Tools", "No tools selected"))
            next_num += 1
        else:
            commands.append((str(next_num), "📂 Enable Tools", "Select tools to use"))
            next_num += 1
            
    if has_system_prompts:
        commands.append((str(next_num), "🔧 Change System", "Select different system prompt"))
        next_num += 1
        
    # Display the menu
    table = Table(box=ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Shortcut", style=self.colors['secondary'], width=10)
    table.add_column("Action", style="bold", width=20)
    table.add_column("Description", style="white")
    
    for cmd, action, desc in commands:
        # Special formatting for shortcuts
        if cmd.isdigit():
            shortcut = f"/{cmd}"
        else:
            shortcut = f"/{cmd}"
        table.add_row(shortcut, action, desc)
        
    # Add help commands
    table.add_row("/help", "📚 Help", "Show all available commands", style="dim")
    table.add_row("/quit", "👋 Exit", "Exit the application", style="dim")
    
    panel = Panel(
        table,
        title="⌨️  Available Commands",
        title_align="left",
        style=self.colors['info'],
        box=ROUNDED
    )
    
    self.console.print(panel)
```

## 4.3 Enhanced Command Processor
**File**: `src/mochi_coco/commands/command_processor.py` (additions)

```python
# Add to imports
from ..tools.discovery_service import ToolDiscoveryService
from ..tools.schema_service import ToolSchemaService
from ..tools.config import ToolSettings, ToolExecutionPolicy
from ..ui.tool_selection_ui import ToolSelectionUI

# Add to CommandProcessor class

def process_command(self, command: str, session: ChatSession, model: str) -> CommandResult:
    """Enhanced command processing with tool commands."""
    command = command.strip().lower()
    
    # Parse command and arguments
    parts = command.split(maxsplit=1)
    cmd = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    # Existing commands...
    if cmd in ['/1', '/chats']:
        return self._handle_chats_command(session)
    elif cmd in ['/2', '/models']:
        return self._handle_models_command()
    # ... other existing commands ...
    
    # Dynamic tool commands (check if number corresponds to tool command)
    command_map = self._build_dynamic_command_map(session)
    if cmd in command_map:
        handler_name = command_map[cmd]
        handler = getattr(self, handler_name, None)
        if handler:
            return handler(session, args)
            
    # Unknown command
    typer.secho(f"Unknown command: {command}", fg=typer.colors.RED)
    return CommandResult()
    
def _build_dynamic_command_map(self, session: ChatSession) -> Dict[str, str]:
    """Build dynamic command mapping based on available features."""
    command_map = {
        '/1': '_handle_chats_command',
        '/2': '_handle_models_command',
        '/3': '_handle_markdown_command',
        '/4': '_handle_thinking_command',
        '/chats': '_handle_chats_command',
        '/models': '_handle_models_command',
        '/markdown': '_handle_markdown_command',
        '/thinking': '_handle_thinking_command',
    }
    
    next_num = 5
    
    # Check if tools are available
    if self._are_tools_available():
        tool_settings = session.get_tool_settings()
        
        if tool_settings and tool_settings.is_enabled():
            # Tool policy command
            command_map[f'/{next_num}'] = '_handle_tool_policy_command'
            command_map['/policy'] = '_handle_tool_policy_command'
            next_num += 1
            
        # Tool selection command
        command_map[f'/{next_num}'] = '_handle_tools_command'
        command_map['/tools'] = '_handle_tools_command'
        next_num += 1
        
    # System prompt command
    if self._are_system_prompts_available():
        command_map[f'/{next_num}'] = '_handle_system_prompt_command'
        command_map['/system'] = '_handle_system_prompt_command'
        next_num += 1
        
    return command_map
    
def _are_tools_available(self) -> bool:
    """Check if tools directory exists and has tools."""
    from pathlib import Path
    tools_dir = Path("./tools")
    return tools_dir.exists() and (tools_dir / "__init__.py").exists()
    
def _are_system_prompts_available(self) -> bool:
    """Check if system prompts are available."""
    return hasattr(self, 'system_prompt_service') and self.system_prompt_service is not None
    
def _handle_tool_policy_command(self, session: ChatSession, args: str = "") -> CommandResult:
    """Handle changing tool execution policy."""
    tool_settings = session.get_tool_settings()
    if not tool_settings:
        tool_settings = ToolSettings()
        
    # Cycle through policies
    policies = list(ToolExecutionPolicy)
    current_index = policies.index(tool_settings.execution_policy)
    next_index = (current_index + 1) % len(policies)
    tool_settings.execution_policy = policies[next_index]
    
    # Update session
    if not hasattr(session.metadata, 'tools_settings'):
        session.metadata.tools_settings = {}
    session.metadata.tools_settings.update(tool_settings.to_dict())
    session.save_session()
    
    # Display confirmation
    policy_name = tool_settings.execution_policy.value.replace('_', ' ').title()
    typer.secho(f"\n✅ Tool execution policy set to: {policy_name}\n", 
                fg=typer.colors.GREEN, bold=True)
    
    return CommandResult()
    
def _handle_tools_command(self, session: ChatSession, args: str = "") -> CommandResult:
    """Handle tool selection command."""
    from ..tools.discovery_service import ToolDiscoveryService
    from ..tools.schema_service import ToolSchemaService
    from ..ui.tool_selection_ui import ToolSelectionUI
    
    # Initialize services
    discovery = ToolDiscoveryService()
    schema_service = ToolSchemaService()
    ui = ToolSelectionUI()
    
    # Handle reload argument
    if args.strip().lower() == 'reload':
        functions, groups = discovery.reload_tools()
        typer.secho("✅ Tools reloaded", fg=typer.colors.GREEN)
    else:
        functions, groups = discovery.discover_tools()
    
    if not functions and not groups:
        typer.secho("\n❌ No tools found. Place Python functions in ./tools/__init__.py\n", 
                   fg=typer.colors.RED)
        
        # Create example file if requested
        if args.strip().lower() == 'init':
            self._create_example_tools_file()
            typer.secho("✅ Created example ./tools/__init__.py", fg=typer.colors.GREEN)
            typer.secho("Reload tools with '/tools reload' to use them", fg=typer.colors.YELLOW)
            
        return CommandResult()
        
    # Get current selection
    tool_settings = session.get_tool_settings() or ToolSettings()
    current_selection = (tool_settings.tools, tool_settings.tool_group)
    
    # Get tool descriptions
    descriptions = schema_service.get_tool_descriptions(functions)
    
    # Display selection menu
    while True:
        ui.display_tool_selection_menu(descriptions, groups, current_selection)
        
        # Get selection
        result = ui.get_tool_selection(len(functions), len(groups))
        
        if result is None:
            # Cancelled
            typer.secho("Tool selection cancelled.", fg=typer.colors.YELLOW)
            return CommandResult()
            
        selected_indices, is_group, special = result
        
        # Handle special commands
        if special == "reload":
            functions, groups = discovery.reload_tools()
            descriptions = schema_service.get_tool_descriptions(functions)
            typer.secho("✅ Tools reloaded", fg=typer.colors.GREEN)
            continue
        elif special == "keep":
            typer.secho("✅ Keeping current selection", fg=typer.colors.GREEN)
            return CommandResult()
            
        # Process selection
        if is_group and selected_indices:
            # Group selection
            group_names = list(groups.keys())
            group_name = group_names[selected_indices[0]]
            tool_settings.tool_group = group_name
            tool_settings.tools = []
            typer.secho(f"\n✅ Tool group '{group_name}' selected\n", fg=typer.colors.GREEN)
        elif selected_indices:
            # Individual tools selection
            tool_names = list(functions.keys())
            selected_tools = [tool_names[i] for i in selected_indices]
            tool_settings.tools = selected_tools
            tool_settings.tool_group = None
            typer.secho(f"\n✅ Selected tools: {', '.join(selected_tools)}\n", fg=typer.colors.GREEN)
        else:
            # Clear selection
            tool_settings.tools = []
            tool_settings.tool_group = None
            typer.secho("\n✅ Tool selection cleared\n", fg=typer.colors.GREEN)
            
        # Update session
        if not hasattr(session.metadata, 'tools_settings'):
            session.metadata.tools_settings = {}
        session.metadata.tools_settings.update(tool_settings.to_dict())
        session.save_session()
        
        # Store updated tools in controller context for next message
        self._update_tool_context(session, functions, groups, schema_service)
        
        return CommandResult()
        
def _create_example_tools_file(self):
    """Create an example tools file."""
    from pathlib import Path
    
    tools_dir = Path("./tools")
    tools_dir.mkdir(exist_ok=True)
    
    example_content = '''"""
User-defined tools for mochi-coco.

Add your tool functions here and include them in __all__ to make them available.
Tool functions should have docstrings and type hints for best results.
"""

def get_current_time() -> str:
    """
    Get the current time in a readable format.
    
    Returns:
        str: Current time as a string
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate_sum(a: float, b: float) -> float:
    """
    Calculate the sum of two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        float: Sum of a and b
    """
    return a + b

# Export tools for use
__all__ = ['get_current_time', 'calculate_sum']

# Optional: Define tool groups
__math__ = ['calculate_sum']
__time__ = ['get_current_time']
'''
    
    init_file = tools_dir / "__init__.py"
    init_file.write_text(example_content)
```

# Phase 5: Testing & Examples

## 5.1 Test Fixtures
**File**: `tests/fixtures/test_tools.py`

```python
"""Test tools for unit testing."""

def mock_successful_tool(arg1: str, arg2: int = 10) -> str:
    """
    A mock tool that always succeeds.
    
    Args:
        arg1: A string argument
        arg2: An integer argument with default
        
    Returns:
        str: A success message
    """
    return f"Success: {arg1} with {arg2}"

def mock_failing_tool() -> str:
    """A mock tool that always fails."""
    raise ValueError("This tool always fails")

def mock_no_docstring_tool():
    return "No docstring"

def mock_no_type_hints_tool(arg1, arg2):
    """Tool without type hints."""
    return f"{arg1} {arg2}"

__all__ = ['mock_successful_tool', 'mock_failing_tool', 
           'mock_no_docstring_tool', 'mock_no_type_hints_tool']

__test_group__ = ['mock_successful_tool', 'mock_failing_tool']
```

## 5.2 Unit Tests
**File**: `tests/test_tool_discovery.py`

```python
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch

from mochi_coco.tools.discovery_service import ToolDiscoveryService

class TestToolDiscovery:
    def test_discover_tools_no_directory(self):
        """Test discovery when tools directory doesn't exist."""
        service = ToolDiscoveryService("/non/existent/path")
        functions, groups = service.discover_tools()
        assert functions == {}
        assert groups == {}
        
    def test_discover_tools_with_fixtures(self, tmp_path):
        """Test discovery with test fixtures."""
        # Copy test fixtures to temp directory
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        
        # Copy test tools
        test_tools = Path(__file__).parent / "fixtures" / "test_tools.py"
        shutil.copy(test_tools, tools_dir / "__init__.py")
        
        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()
        
        assert 'mock_successful_tool' in functions
        assert 'mock_failing_tool' in functions
        assert 'test_group' in groups
        assert 'mock_successful_tool' in groups['test_group']
        
    def test_reload_tools(self, tmp_path):
        """Test reloading tools after changes."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        
        # Initial content
        init_content = '''
def tool1():
    """Tool 1"""
    return "1"
    
__all__ = ['tool1']
'''
        (tools_dir / "__init__.py").write_text(init_content)
        
        service = ToolDiscoveryService(str(tools_dir))
        functions, _ = service.discover_tools()
        assert 'tool1' in functions
        assert 'tool2' not in functions
        
        # Update content
        updated_content = '''
def tool1():
    """Tool 1"""
    return "1"
    
def tool2():
    """Tool 2"""
    return "2"
    
__all__ = ['tool1', 'tool2']
'''
        (tools_dir / "__init__.py").write_text(updated_content)
        
        # Reload
        functions, _ = service.reload_tools()
        assert 'tool1' in functions
        assert 'tool2' in functions
```

## 5.3 Integration Tests
**File**: `tests/test_tool_execution.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock

from mochi_coco.tools.execution_service import ToolExecutionService, ToolExecutionResult
from mochi_coco.tools.config import ToolExecutionPolicy

class TestToolExecution:
    def test_execute_successful_tool(self):
        """Test successful tool execution."""
        def test_tool(x: int) -> str:
            return f"Result: {x}"
            
        service = ToolExecutionService({'test_tool': test_tool})
        result = service.execute_tool('test_tool', {'x': 42}, 
                                     ToolExecutionPolicy.NEVER_CONFIRM)
        
        assert result.success
        assert result.result == "Result: 42"
        assert result.tool_name == 'test_tool'
        assert result.execution_time > 0
        
    def test_execute_nonexistent_tool(self):
        """Test execution of non-existent tool."""
        service = ToolExecutionService({})
        result = service.execute_tool('missing_tool', {}, 
                                     ToolExecutionPolicy.NEVER_CONFIRM)
        
        assert not result.success
        assert "not found" in result.error_message.lower()
        
    def test_execute_with_invalid_arguments(self):
        """Test execution with invalid arguments."""
        def test_tool(x: int) -> str:
            return f"Result: {x}"
            
        service = ToolExecutionService({'test_tool': test_tool})
        result = service.execute_tool('test_tool', {'y': 42},  # wrong arg name
                                     ToolExecutionPolicy.NEVER_CONFIRM)
        
        assert not result.success
        assert "invalid arguments" in result.error_message.lower()
        
    def test_execute_with_confirmation(self):
        """Test execution with confirmation callback."""
        def test_tool() -> str:
            return "Success"
            
        service = ToolExecutionService({'test_tool': test_tool})
        
        # Test approval
        confirm_callback = Mock(return_value=True)
        result = service.execute_tool('test_tool', {}, 
                                     ToolExecutionPolicy.ALWAYS_CONFIRM,
                                     confirm_callback)
        
        assert result.success
        assert confirm_callback.called
        
        # Test denial
        confirm_callback = Mock(return_value=False)
        result = service.execute_tool('test_tool', {}, 
                                     ToolExecutionPolicy.ALWAYS_CONFIRM,
                                     confirm_callback)
        
        assert not result.success
        assert "denied by user" in result.error_message.lower()
```

## 5.4 Example Tools Collection
**File**: `examples/tools/__init__.py`

```python
"""
Example tools collection for mochi-coco.

This file demonstrates various tool patterns and best practices.
"""

import json
import random
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

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
        "line_count": len(text.splitlines())
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

# === Math Tools ===

def calculate(expression: str) -> float:
    """
    Evaluate a mathematical expression safely.
    
    Args:
        expression: Mathematical expression (e.g., "2 + 2 * 3")
        
    Returns:
        float: Result of the calculation
    """
    # Safe evaluation - only allow certain operations
    allowed_names = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
    }
    
    # Only allow basic math operations
    allowed_chars = set('0123456789+-*/()., ')
    if not all(c in allowed_chars for c in expression):
        raise ValueError(f"Invalid characters in expression: {expression}")
    
    try:
        # Use compile and eval for safer evaluation
        code = compile(expression, '<string>', 'eval')
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return float(result)
    except Exception as e:
        raise ValueError(f"Could not evaluate expression: {e}")

def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert temperature between Celsius, Fahrenheit, and Kelvin.
    
    Args:
        value: Temperature value
        from_unit: Source unit (C, F, or K)
        to_unit: Target unit (C, F, or K)
        
    Returns:
        float: Converted temperature
    """
    from_unit = from_unit.upper()
    to_unit = to_unit.upper()
    
    # Convert to Celsius first
    if from_unit == 'C':
        celsius = value
    elif from_unit == 'F':
        celsius = (value - 32) * 5/9
    elif from_unit == 'K':
        celsius = value - 273.15
    else:
        raise ValueError(f"Unknown unit: {from_unit}")
    
    # Convert from Celsius to target
    if to_unit == 'C':
        return celsius
    elif to_unit == 'F':
        return celsius * 9/5 + 32
    elif to_unit == 'K':
        return celsius + 273.15
    else:
        raise ValueError(f"Unknown unit: {to_unit}")

# === JSON Tools ===

def parse_json(json_string: str) -> Dict[str, Any]:
    """
    Parse a JSON string and return the result.
    
    Args:
        json_string: JSON string to parse
        
    Returns:
        dict: Parsed JSON object
    """
    return json.loads(json_string)

def format_json(data: Dict[str, Any], indent: int = 2) -> str:
    """
    Format a dictionary as pretty-printed JSON.
    
    Args:
        data: Dictionary to format
        indent: Number of spaces for indentation
        
    Returns:
        str: Formatted JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)

# Export all tools
__all__ = [
    'get_current_datetime',
    'generate_random_number',
    'count_words',
    'reverse_text',
    'calculate',
    'convert_temperature',
    'parse_json',
    'format_json',
]

# Tool groups for organized access
__utility__ = ['get_current_datetime', 'generate_random_number']
__text__ = ['count_words', 'reverse_text']
__math__ = ['calculate', 'convert_temperature']
__json__ = ['parse_json', 'format_json']
```

## 5.5 End-to-End Test
**File**: `tests/test_e2e_tools.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from mochi_coco.chat_controller import ChatController
from mochi_coco.chat.session import ChatSession

@pytest.mark.integration
class TestToolsE2E:
    """End-to-end tests for tool functionality."""
    
    @patch('mochi_coco.ollama.client.Client')
    def test_tool_execution_flow(self, mock_client, tmp_path):
        """Test complete tool execution flow."""
        # Setup
        controller = ChatController()
        session = ChatSession("test-model", sessions_dir=str(tmp_path))
        
        # Create mock tool
        def test_tool(x: int) -> str:
            """Test tool"""
            return f"Result: {x}"
        
        # Mock chat response with tool call
        mock_response = MagicMock()
        mock_response.message.content = ""
        mock_response.message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name='test_tool',
                    arguments={'x': 42}
                )
            )
        ]
        mock_response.done = True
        
        mock_client.return_value.chat.return_value = [mock_response]
        
        # Test tool execution with context
        tool_context = {
            'tools_enabled': True,
            'tools': [test_tool],
            'tool_settings': MagicMock(execution_policy='never_confirm'),
            'tool_execution_service': MagicMock()
        }
        
        # Process message
        with patch.object(controller.session_controller, 'process_user_message') as mock_process:
            mock_process.return_value = MagicMock(success=True)
            
            controller.session_controller.process_user_message(
                session, "test-model", "Use the test tool with x=42", 
                controller.renderer, tool_context
            )
            
            assert mock_process.called
```

## 5.6 Documentation
**File**: `docs/tools_user_guide.md`

```python
# Custom Tools User Guide

## Quick Start

1. Create a `./tools` directory in your project
2. Add an `__init__.py` file with your tool functions
3. Export functions in `__all__`
4. Start mochi-coco and select tools with `/tools`

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

### Best Practices

1. **Always include docstrings** - The LLM uses these to understand your tools
2. **Use type hints** - Helps with validation and schema generation
3. **Return strings** - LLMs work best with string outputs
4. **Handle errors gracefully** - Return error messages rather than raising exceptions
5. **Keep tools focused** - Each tool should do one thing well

### Tool Groups

Organize related tools into groups:

```python
__math__ = ['add', 'subtract', 'multiply']
__text__ = ['uppercase', 'lowercase', 'word_count']
```

## Using Tools in Chat

### Selecting Tools

- `/tools` - Open tool selection menu
- `/tools reload` - Reload tools after changes
- `/tools init` - Create example tools file

### Tool Execution Policies

- **Always Confirm** - Ask before every tool execution
- **Never Confirm** - Execute tools automatically
- **Confirm Destructive** - Only confirm potentially dangerous operations (future)

Toggle with `/5` or `/policy` command.

### Example Session

```
You: What's 2 + 2?

🔧 AI requesting tool: calculate
⚠️ Allow execution? [y/N]: y
✓ Tool 'calculate' executed successfully