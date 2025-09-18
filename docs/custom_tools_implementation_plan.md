# Custom Tools Implementation Plan

## Overview

This document outlines the detailed implementation plan for the Custom Tools feature in mochi-coco, aligned with the feature specification and leveraging Ollama's built-in tool utilities.

## Implementation Phases

### Phase 1: Core Infrastructure
**Estimated Time**: 3-4 days  
**Goal**: Establish tool discovery, leverage Ollama's schema conversion, and create selection UI

### Phase 2: Tool Execution & Confirmation System
**Estimated Time**: 2-3 days  
**Goal**: Implement tool execution with toggleable confirmation

### Phase 3: Streaming Integration
**Estimated Time**: 3-4 days  
**Goal**: Integrate tool calls into streaming chat flow

### Phase 4: Session Persistence & UI Polish
**Estimated Time**: 2-3 days  
**Goal**: Store tool settings in sessions and enhance UI

### Phase 5: Testing & Examples
**Estimated Time**: 2-3 days  
**Goal**: Comprehensive testing and example tools

## Detailed Implementation

### Phase 1: Core Infrastructure

#### 1.1 Tool Discovery Service
**File**: `src/mochi_coco/tools/discovery_service.py`

```python
from typing import Dict, List, Tuple, Callable, Optional, Any
import os
import sys
import importlib.util
import inspect
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ToolDiscoveryService:
    """Service for discovering and loading user-defined tools."""
    
    def __init__(self, tools_dir: str = "./tools"):
        self.tools_dir = Path(tools_dir)
        self.available_functions: Dict[str, Callable] = {}
        self.tool_groups: Dict[str, List[str]] = {}
        
    def discover_tools(self) -> Tuple[Dict[str, Callable], Dict[str, List[str]]]:
        """
        Discover tools from the tools directory.
        
        Returns:
            Tuple of (individual_tools, tool_groups)
        """
        if not self.tools_dir.exists():
            logger.debug(f"Tools directory {self.tools_dir} does not exist")
            return {}, {}
            
        init_file = self.tools_dir / "__init__.py"
        if not init_file.exists():
            logger.warning(f"No __init__.py found in {self.tools_dir}")
            return {}, {}
            
        module = self._load_tools_module()
        if module:
            self.available_functions, self.tool_groups = self._extract_tools_from_module(module)
            
        return self.available_functions, self.tool_groups
        
    def _load_tools_module(self) -> Optional[object]:
        """Load the tools module from __init__.py"""
        try:
            # Add tools directory to path temporarily
            sys.path.insert(0, str(self.tools_dir.parent))
            
            spec = importlib.util.spec_from_file_location(
                "tools", self.tools_dir / "__init__.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            return module
        except Exception as e:
            logger.error(f"Failed to load tools module: {e}")
            return None
        finally:
            # Clean up path
            if str(self.tools_dir.parent) in sys.path:
                sys.path.remove(str(self.tools_dir.parent))
                
    def _extract_tools_from_module(self, module) -> Tuple[Dict[str, Callable], Dict[str, List[str]]]:
        """Extract tools and groups from the loaded module"""
        individual_tools = {}
        tool_groups = {}
        
        # Extract individual tools from __all__
        if hasattr(module, '__all__'):
            for tool_name in module.__all__:
                if hasattr(module, tool_name):
                    func = getattr(module, tool_name)
                    if callable(func) and self._validate_tool_function(func):
                        individual_tools[tool_name] = func
                        
        # Extract tool groups (variables with __name__ pattern)
        for attr_name in dir(module):
            if attr_name.startswith('__') and attr_name.endswith('__') and attr_name not in ['__all__', '__doc__', '__file__', '__name__', '__package__']:
                group_name = attr_name.strip('_')
                tool_list = getattr(module, attr_name)
                if isinstance(tool_list, list):
                    # Validate that all tools in group exist
                    valid_tools = []
                    for tool_name in tool_list:
                        if tool_name in individual_tools:
                            valid_tools.append(tool_name)
                        else:
                            logger.warning(f"Tool {tool_name} in group {group_name} not found in __all__")
                    if valid_tools:
                        tool_groups[group_name] = valid_tools
                        
        return individual_tools, tool_groups
        
    def _validate_tool_function(self, func: Callable) -> bool:
        """Validate that a function meets tool requirements"""
        # Check for docstring
        if not inspect.getdoc(func):
            logger.warning(f"Function {func.__name__} has no docstring")
            return False
            
        # Check for type hints
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                logger.warning(f"Function {func.__name__} parameter {param_name} missing type hint")
                
        return True
```

#### 1.2 Tool Schema Service
**File**: `src/mochi_coco/tools/schema_service.py`

```python
from typing import List, Dict, Callable, Optional
from ollama import Tool
from ollama._utils import convert_function_to_tool, _parse_docstring
import inspect
import logging

logger = logging.getLogger(__name__)

class ToolSchemaService:
    """Service for converting Python functions to Ollama tool schemas."""
    
    def convert_functions_to_tools(self, functions: Dict[str, Callable]) -> Dict[str, Tool]:
        """
        Convert dictionary of functions to Ollama Tool objects.
        
        Returns:
            Dictionary mapping function names to Tool objects
        """
        tools = {}
        for name, func in functions.items():
            try:
                # Use Ollama's built-in conversion
                tool = convert_function_to_tool(func)
                tools[name] = tool
            except Exception as e:
                logger.error(f"Failed to convert function {name} to tool: {e}")
                
        return tools
        
    def get_tool_descriptions(self, functions: Dict[str, Callable]) -> Dict[str, str]:
        """
        Extract descriptions from function docstrings for UI display.
        
        Uses Ollama's _parse_docstring to handle various docstring formats.
        """
        descriptions = {}
        for name, func in functions.items():
            docstring = inspect.getdoc(func)
            if docstring:
                parsed = _parse_docstring(docstring)
                # The main description is stored under the hash key
                doc_hash = str(hash(docstring))
                description = parsed.get(doc_hash, "").strip()
                # Take first line for UI display
                descriptions[name] = description.split('\n')[0] if description else f"Function {name}"
            else:
                descriptions[name] = f"Function {name}"
                
        return descriptions
```

#### 1.3 Tool Selection UI
**File**: `src/mochi_coco/ui/tool_selection_ui.py`

```python
from typing import Dict, List, Optional, Tuple
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group
from rich.text import Text
from rich.box import ROUNDED

class ToolSelectionUI:
    """UI for selecting tools and tool groups."""
    
    def __init__(self):
        self.console = Console()
        self.colors = {
            'primary': '#87CEEB',
            'secondary': '#B0C4DE',
            'warning': '#FFD700',
            'success': '#90EE90',
            'error': '#FFB6C1',
            'info': '#87CEEB'
        }
        
    def display_tool_selection_menu(self, 
                                   individual_tools: Dict[str, str], 
                                   tool_groups: Dict[str, List[str]]) -> None:
        """Display the tool selection menu using Rich."""
        
        # Create single tools table
        single_table = Table(box=ROUNDED, show_header=True, header_style=self.colors['secondary'])
        single_table.add_column("#", style=self.colors['secondary'], width=5)
        single_table.add_column("Tool Name", style="bold", width=25)
        single_table.add_column("Tool Description", style="white")
        
        for i, (tool_name, description) in enumerate(individual_tools.items(), 1):
            single_table.add_row(str(i), tool_name, description)
            
        # Create tool groups table
        group_table = Table(box=ROUNDED, show_header=True, header_style=self.colors['secondary'])
        group_table.add_column("#", style=self.colors['secondary'], width=5)
        group_table.add_column("Tool Group", style="bold", width=25)
        group_table.add_column("Tools Included", style="white")
        
        for i, (group_name, tools) in enumerate(tool_groups.items()):
            letter = chr(ord('a') + i)
            tools_str = ", ".join(tools)
            group_table.add_row(letter, group_name, tools_str)
            
        # Create options text
        options_text = Text()
        options_text.append("\n💡 Options:\n", style="bold bright_yellow")
        options_text.append(f"• 🔢 Select multiple tools (1-{len(individual_tools)}) by listing them (e.g. 1,3,4)\n", style="white")
        options_text.append(f"• 📂 Select a tool group by choosing a letter (a-{chr(ord('a') + len(tool_groups) - 1)})\n", style="white")
        options_text.append("• ❌ Type 'none' to choose no tools\n", style="white")
        options_text.append("• 👋 Type 'q' to quit", style="white")
        
        # Combine all elements
        content = Group(
            Text("Single tools", style="bold"),
            single_table,
            Text("\nTool groups", style="bold"),
            group_table,
            options_text
        )
        
        panel = Panel(
            content,
            title="🛠️ Available Tools",
            title_align="left",
            style=self.colors['info'],
            box=ROUNDED
        )
        
        self.console.print(panel)
        
    def get_tool_selection(self, num_tools: int, num_groups: int) -> Optional[Tuple[List[str], bool, Optional[str]]]:
        """
        Get user's tool selection.
        
        Args:
            num_tools: Number of individual tools available
            num_groups: Number of tool groups available
            
        Returns:
            Tuple of (selected_tool_indices_or_group, is_group_selection, group_letter) or None if cancelled
        """
        from ..ui.user_interaction import UserInteraction
        
        user_interaction = UserInteraction()
        choice = user_interaction.get_user_input().strip().lower()
        
        if choice in {'q', 'quit', 'exit'}:
            return None
            
        if choice == 'none':
            return ([], False, None)
            
        # Check for group selection (single letter)
        if len(choice) == 1 and choice.isalpha():
            group_index = ord(choice) - ord('a')
            if 0 <= group_index < num_groups:
                return ([group_index], True, choice)
            else:
                self.console.print(f"[red]Invalid group selection: {choice}[/red]")
                return None
                
        # Check for individual tool selection (comma-separated numbers)
        try:
            selected = []
            for part in choice.split(','):
                tool_num = int(part.strip())
                if 1 <= tool_num <= num_tools:
                    selected.append(tool_num - 1)  # Convert to 0-based
                else:
                    self.console.print(f"[red]Invalid tool number: {tool_num}[/red]")
                    return None
            return (selected, False, None)
        except ValueError:
            self.console.print(f"[red]Invalid selection format: {choice}[/red]")
            return None
```

#### 1.4 Tool Configuration
**File**: `src/mochi_coco/tools/config.py`

```python
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class ToolSettings:
    """Tool settings for a session."""
    tools: List[str] = field(default_factory=list)
    tool_group: Optional[str] = None
    confirmation_necessary: bool = True
    
    def is_enabled(self) -> bool:
        """Check if any tools are enabled."""
        return bool(self.tools or self.tool_group)
        
    def get_active_tools(self, all_tools: Dict[str, any], 
                         tool_groups: Dict[str, List[str]]) -> List[str]:
        """Get list of active tool names based on settings."""
        if self.tool_group and self.tool_group in tool_groups:
            return tool_groups[self.tool_group]
        return self.tools
```

### Phase 2: Tool Execution & Confirmation System

#### 2.1 Tool Execution Service
**File**: `src/mochi_coco/tools/execution_service.py`

```python
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass
import traceback
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class ToolExecutionResult:
    """Result of tool execution."""
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time: float = 0.0

class ToolExecutionService:
    """Service for safely executing user tools."""
    
    def __init__(self, available_functions: Dict[str, Callable]):
        self.available_functions = available_functions
        
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """
        Execute a tool with given arguments.
        
        Args:
            tool_name: Name of the tool function
            arguments: Dictionary of arguments to pass to the function
            
        Returns:
            ToolExecutionResult with success status and result/error
        """
        start_time = time.time()
        
        if not self._validate_tool_exists(tool_name):
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message=f"Tool '{tool_name}' not found",
                execution_time=time.time() - start_time
            )
            
        try:
            func = self.available_functions[tool_name]
            result = func(**arguments)
            
            return ToolExecutionResult(
                success=True,
                result=str(result),  # Ensure result is string for LLM
                execution_time=time.time() - start_time
            )
            
        except TypeError as e:
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message=f"Invalid arguments for tool '{tool_name}': {e}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message=f"Tool execution failed: {str(e)}",
                execution_time=time.time() - start_time
            )
            
    def _validate_tool_exists(self, tool_name: str) -> bool:
        """Validate that the requested tool exists."""
        return tool_name in self.available_functions
```

#### 2.2 Tool Confirmation UI
**File**: `src/mochi_coco/ui/tool_confirmation_ui.py`

```python
from typing import Dict, Any
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.box import ROUNDED
import json

class ToolConfirmationUI:
    """UI for confirming tool execution."""
    
    def __init__(self):
        self.console = Console()
        
    def confirm_tool_execution(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Display confirmation prompt for tool execution.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments that will be passed to the tool
            
        Returns:
            True if user confirms, False otherwise
        """
        # Format arguments for display
        args_str = self._format_arguments(arguments)
        
        # Create confirmation panel
        content = Text()
        content.append("🛠️ Tool Call Request:\n\n", style="bold yellow")
        content.append(f"Function: ", style="bold")
        content.append(f"{tool_name}\n", style="cyan")
        content.append(f"Arguments: ", style="bold")
        content.append(f"{args_str}\n\n", style="green")
        content.append("Allow execution? [y/N]: ", style="bold white")
        
        panel = Panel(
            content,
            title="⚠️  Tool Execution Confirmation",
            title_align="left",
            style="yellow",
            box=ROUNDED
        )
        
        self.console.print(panel)
        
        # Get user confirmation (not added to chat history)
        try:
            response = input().strip().lower()
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False
            
    def _format_arguments(self, arguments: Dict[str, Any]) -> str:
        """Format arguments for display in confirmation prompt."""
        try:
            # Pretty print JSON for better readability
            return json.dumps(arguments, indent=2, ensure_ascii=False)
        except:
            # Fallback to string representation
            return str(arguments)
```

### Phase 3: Streaming Integration

#### 3.1 Tool-Aware Renderer
**File**: `src/mochi_coco/rendering/tool_aware_renderer.py`

```python
from typing import Iterator, Dict, Callable, List, Optional, Any
from ollama import ChatResponse, Message, Tool
from ..tools.execution_service import ToolExecutionService
from ..ui.tool_confirmation_ui import ToolConfirmationUI
from ..tools.config import ToolSettings
import logging

logger = logging.getLogger(__name__)

class ToolAwareRenderer:
    """Enhanced renderer that handles tool calls during streaming."""
    
    def __init__(self, base_renderer, tool_execution_service: Optional[ToolExecutionService] = None,
                 confirmation_ui: Optional[ToolConfirmationUI] = None):
        self.base_renderer = base_renderer
        self.tool_execution_service = tool_execution_service
        self.confirmation_ui = confirmation_ui or ToolConfirmationUI()
        
    def render_streaming_response_with_tools(self, 
                                           text_chunks: Iterator[ChatResponse],
                                           tool_settings: ToolSettings,
                                           session: "ChatSession",
                                           model: str,
                                           client: "OllamaClient") -> Optional[ChatResponse]:
        """
        Render streaming response handling tool calls.
        
        This method:
        1. Streams text content normally
        2. Detects tool calls and pauses streaming
        3. Prompts user for confirmation if enabled
        4. Executes approved tools
        5. Continues streaming with tool results
        """
        accumulated_text = ""
        final_chunk = None
        
        for chunk in text_chunks:
            # Handle thinking blocks if present
            if hasattr(chunk.message, 'thinking') and chunk.message.thinking:
                if self.base_renderer.show_thinking:
                    print(chunk.message.thinking, end='', flush=True)
                    
            # Handle regular content
            if chunk.message.content:
                accumulated_text += chunk.message.content
                print(chunk.message.content, end='', flush=True)
                
            # Handle tool calls
            if chunk.message.tool_calls:
                # Process each tool call
                for tool_call in chunk.message.tool_calls:
                    tool_result = self._handle_tool_call(
                        tool_call, 
                        tool_settings
                    )
                    
                    if tool_result:
                        # Add tool call message to session
                        session.add_tool_call_message(
                            tool_calls=[tool_call.model_dump()],
                            model=model
                        )
                        
                        # Add tool response to session
                        session.add_tool_response_message(
                            tool_name=tool_call.function.name,
                            content=tool_result
                        )
                        
                        # Continue conversation with tool result
                        messages = session.get_messages_for_api()
                        
                        # Get available tools for continued streaming
                        available_tools = self._get_available_tools(tool_settings)
                        
                        # Continue streaming with updated context
                        continuation_stream = client.chat_stream(
                            model, 
                            messages, 
                            tools=available_tools
                        )
                        
                        # Recursively handle continuation (might have more tool calls)
                        return self.render_streaming_response_with_tools(
                            continuation_stream,
                            tool_settings,
                            session,
                            model,
                            client
                        )
                        
            # Check if this is the final chunk
            if chunk.done:
                chunk.message.content = accumulated_text
                final_chunk = chunk
                
        return final_chunk
        
    def _handle_tool_call(self, tool_call: Any, tool_settings: ToolSettings) -> Optional[str]:
        """
        Handle a single tool call with optional confirmation.
        
        Returns:
            Tool result string or None if execution was denied/failed
        """
        if not self.tool_execution_service:
            logger.error("Tool execution service not available")
            return None
            
        tool_name = tool_call.function.name
        arguments = dict(tool_call.function.arguments)
        
        # Check if confirmation is needed
        if tool_settings.confirmation_necessary:
            if not self.confirmation_ui.confirm_tool_execution(tool_name, arguments):
                print("\n[Tool execution denied by user]")
                return "Tool execution denied by user"
                
        # Execute the tool
        result = self.tool_execution_service.execute_tool(tool_name, arguments)
        
        if result.success:
            print(f"\n[Tool '{tool_name}' executed successfully]")
            return result.result
        else:
            print(f"\n[Tool '{tool_name}' failed: {result.error_message}]")
            return f"Tool execution failed: {result.error_message}"
            
    def _get_available_tools(self, tool_settings: ToolSettings) -> Optional[List[Tool]]:
        """Get list of available Tool objects based on settings."""
        # This would need to be passed from the controller
        # For now, return None to indicate tools should be retrieved from context
        return None
```

#### 3.2 Enhanced Session Types
**File**: `src/mochi_coco/chat/session.py` (additions)

```python
# Add to existing session.py file

@dataclass
class ToolCallMessage:
    """A message representing an assistant's tool call."""
    role: str = "assistant"
    content: str = ""
    tool_calls: List[Dict] = None
    model: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: Optional[str] = None
    eval_count: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4()).replace("-", "")[:10]
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.tool_calls is None:
            self.tool_calls = []

@dataclass
class ToolResponseMessage:
    """A message representing a tool's response."""
    role: str = "tool"
    tool_name: str = ""
    content: str = ""
    message_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4()).replace("-", "")[:10]
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

# Add these methods to ChatSession class:

def add_tool_call_message(self, tool_calls: List[Dict], model: str, 
                         content: str = "", **kwargs) -> None:
    """Add a tool call message to the session."""
    message = ToolCallMessage(
        content=content,
        tool_calls=tool_calls,
        model=model,
        **kwargs
    )
    self.messages.append(message)
    self.metadata.message_count = len(self.messages)
    self.metadata.updated_at = datetime.now().isoformat()
    self.save_session()
    
def add_tool_response_message(self, tool_name: str, content: str, **kwargs) -> None:
    """Add a tool response message to the session."""
    message = ToolResponseMessage(
        tool_name=tool_name,
        content=content,
        **kwargs
    )
    self.messages.append(message)
    self.metadata.message_count = len(self.messages)
    self.metadata.updated_at = datetime.now().isoformat()
    self.save_session()
    
def update_tool_settings(self, tools_settings: Dict[str, Any]) -> None:
    """Update tool settings in metadata."""
    if not hasattr(self.metadata, 'tools_settings'):
        self.metadata.tools_settings = {}
    self.metadata.tools_settings.update(tools_settings)
    self.save_session()
```

### Phase 4: Session Persistence & UI Polish

#### 4.1 Enhanced Menu System
**File**: `src/mochi_coco/ui/menu_display.py` (modifications)

```python
# Modifications to display_command_menu method

def display_command_menu(self, has_system_prompts: bool = False, 
                        has_tools: bool = False, 
                        tools_confirmation_enabled: bool = True) -> None:
    """Enhanced command menu with tool options."""
    
    commands = [
        ("1", "💬 Switch Sessions", "Change to different chat session"),
        ("2", "🤖 Change Model", "Select a different AI model"),
        ("3", "📝 Toggle Markdown", "Enable/disable markdown rendering"),
        ("4", "🤔 Toggle Thinking", "Show/hide thinking blocks")
    ]
    
    if has_tools:
        confirmation_status = "enabled" if tools_confirmation_enabled else "disabled"
        commands.append(("5", "🛠️ Tool Confirmation", f"Confirmation is {confirmation_status}"))
        commands.append(("6", "📂 Change Tools", "Select different tools/groups"))
        
    if has_system_prompts:
        next_num = "7" if has_tools else "5"
        commands.append((next_num, "🔧 Change System", "Select different system prompt"))
        
    # Rest of the implementation...
```

#### 4.2 Enhanced Command Processor
**File**: `src/mochi_coco/commands/command_processor.py` (additions)

```python
# Add to CommandProcessor class

def _handle_tool_confirmation_toggle(self, session: "ChatSession") -> CommandResult:
    """Handle toggling tool confirmation on/off."""
    if not hasattr(session.metadata, 'tools_settings'):
        session.metadata.tools_settings = {'confirmation_necessary': True}
        
    current = session.metadata.tools_settings.get('confirmation_necessary', True)
    session.metadata.tools_settings['confirmation_necessary'] = not current
    session.save_session()
    
    status = "enabled" if not current else "disabled"
    typer.secho(f"\n✅ Tool confirmation {status}\n", fg=typer.colors.GREEN, bold=True)
    
    return CommandResult()
    
def _handle_change_tools_command(self, session: "ChatSession") -> CommandResult:
    """Handle changing selected tools."""
    from ..tools.discovery_service import ToolDiscoveryService
    from ..tools.schema_service import ToolSchemaService
    from ..ui.tool_selection_ui import ToolSelectionUI
    
    # Discover available tools
    discovery = ToolDiscoveryService()
    functions, groups = discovery.discover_tools()
    
    if not functions and not groups:
        typer.secho("\n❌ No tools found in ./tools directory\n", fg=typer.colors.RED)
        return CommandResult()
        
    # Get tool descriptions
    schema_service = ToolSchemaService()
    descriptions = schema_service.get_tool_descriptions(functions)
    
    # Display selection menu
    ui = ToolSelectionUI()
    ui.display_tool_selection_menu(descriptions, groups)
    
    # Get selection
    result = ui.get_tool_selection(len(functions), len(groups))
    
    if result is None:
        typer.secho("Tool selection cancelled.", fg=typer.colors.YELLOW)
        return CommandResult()
        
    selected_indices, is_group, group_letter = result
    
    # Update session tool settings
    if not hasattr(session.metadata, 'tools_settings'):
        session.metadata.tools_settings = {}
        
    if is_group and selected_indices:
        # Group selection
        group_names = list(groups.keys())
        group_name = group_names[selected_indices[0]]
        session.metadata.tools_settings['tool_group'] = group_name
        session.metadata.tools_settings['tools'] = []
        typer.secho(f"\n✅ Tool group '{group_name}' selected\n", fg=typer.colors.GREEN)
    elif selected_indices:
        # Individual tools selection
        tool_names = list(functions.keys())
        selected_tools = [tool_names[i] for i in selected_indices]
        session.metadata.tools_settings['tools'] = selected_tools
        session.metadata.tools_settings['tool_group'] = None
        typer.secho(f"\n✅ Selected tools: {', '.join(selected_tools)}\n", fg=typer.colors.GREEN)
    else:
        # No tools selected
        session.metadata.tools_settings['