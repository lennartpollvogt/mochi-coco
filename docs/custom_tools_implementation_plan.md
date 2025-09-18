# Custom Tools Implementation Plan

## Overview

This document outlines the detailed implementation plan for the Custom Tools feature in mochi-coco. The implementation will be divided into phases to ensure a systematic and testable approach.

## Implementation Phases

### Phase 1: Core Infrastructure
**Estimated Time**: 3-4 days  
**Goal**: Establish basic tool discovery, schema conversion, and selection UI

### Phase 2: Tool Execution & Security
**Estimated Time**: 2-3 days  
**Goal**: Implement safe tool execution with user confirmation

### Phase 3: Streaming Integration
**Estimated Time**: 3-4 days  
**Goal**: Integrate tool calls into streaming chat flow

### Phase 4: Session Persistence & UI Polish
**Estimated Time**: 2-3 days  
**Goal**: Store tool calls in sessions and enhance UI

### Phase 5: Testing & Examples
**Estimated Time**: 2-3 days  
**Goal**: Comprehensive testing and example tools

## Detailed Implementation

### Phase 1: Core Infrastructure

#### 1.1 Tool Discovery Service
**File**: `src/mochi_coco/tools/discovery_service.py`

```python
from typing import Dict, List, Tuple, Callable, Optional
import os
import sys
import importlib.util
import inspect
from pathlib import Path

class ToolDiscoveryService:
    """Service for discovering and loading user-defined tools."""
    
    def __init__(self, tools_dir: str = "./tools"):
        self.tools_dir = Path(tools_dir)
        
    def discover_tools(self) -> Tuple[Dict[str, Callable], Dict[str, List[str]]]:
        """
        Discover tools from the tools directory.
        
        Returns:
            Tuple of (individual_tools, tool_groups)
        """
        
    def _load_tools_module(self) -> Optional[object]:
        """Load the tools module from __init__.py"""
        
    def _extract_tools_from_module(self, module) -> Tuple[Dict[str, Callable], Dict[str, List[str]]]:
        """Extract tools and groups from the loaded module"""
        
    def _validate_tool_function(self, func: Callable) -> bool:
        """Validate that a function meets tool requirements"""
```

**Key responsibilities**:
- Scan `tools/` directory for `__init__.py`
- Load and validate tool modules
- Extract `__all__` and `__groupname__` variables
- Validate function signatures and docstrings
- Handle import errors gracefully

#### 1.2 Tool Schema Service
**File**: `src/mochi_coco/tools/schema_service.py`

```python
from typing import List, Dict, Callable
from ollama import Tool
from ollama._utils import convert_function_to_tool

class ToolSchemaService:
    """Service for converting Python functions to Ollama tool schemas."""
    
    def convert_functions_to_tools(self, functions: Dict[str, Callable]) -> List[Tool]:
        """Convert dictionary of functions to Ollama Tool objects."""
        
    def get_tool_descriptions(self, functions: Dict[str, Callable]) -> Dict[str, str]:
        """Extract descriptions from function docstrings for UI display."""
```

**Key responsibilities**:
- Use ollama-python's `convert_function_to_tool()`
- Extract descriptions for UI display
- Handle conversion errors gracefully

#### 1.3 Tool Selection UI
**File**: `src/mochi_coco/ui/tool_selection_ui.py`

```python
from typing import Dict, List, Optional, Tuple
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

class ToolSelectionUI:
    """UI for selecting tools and tool groups."""
    
    def display_tool_selection_menu(self, individual_tools: Dict[str, str], 
                                   tool_groups: Dict[str, List[str]]) -> None:
        """Display the tool selection menu using Rich."""
        
    def get_tool_selection(self) -> Optional[Tuple[List[str], bool]]:
        """
        Get user's tool selection.
        
        Returns:
            Tuple of (selected_tools, is_group_selection) or None if cancelled
        """
```

**Integration points**:
- Extend `MenuDisplay` class to include tool selection
- Add tool selection to session creation flow
- Update `CommandProcessor` for tool menu commands

#### 1.4 Tool Configuration Service
**File**: `src/mochi_coco/tools/config_service.py`

```python
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ToolConfig:
    """Configuration for tool usage in a session."""
    enabled: bool = False
    selected_tools: List[str] = None
    tool_group: Optional[str] = None
    
class ToolConfigService:
    """Service for managing tool configuration per session."""
    
    def create_tool_config(self, selected_tools: List[str], 
                          is_group: bool = False, 
                          group_name: str = None) -> ToolConfig:
        """Create tool configuration from user selection."""
        
    def is_tools_enabled(self, config: ToolConfig) -> bool:
        """Check if tools are enabled in configuration."""
```

### Phase 2: Tool Execution & Security

#### 2.1 Tool Execution Service
**File**: `src/mochi_coco/tools/execution_service.py`

```python
from typing import Dict, Callable, Any, Optional
import traceback
import time

class ToolExecutionResult:
    """Result of tool execution."""
    success: bool
    result: Any
    error_message: Optional[str]
    execution_time: float

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
        
    def _validate_tool_exists(self, tool_name: str) -> bool:
        """Validate that the requested tool exists."""
        
    def _execute_with_timeout(self, func: Callable, args: Dict[str, Any], 
                             timeout: int = 30) -> Any:
        """Execute function with timeout (future enhancement)."""
```

#### 2.2 Tool Confirmation UI
**File**: `src/mochi_coco/ui/tool_confirmation_ui.py`

```python
from typing import Dict, Any
from rich.panel import Panel
from rich.console import Console
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
        
    def _format_arguments(self, arguments: Dict[str, Any]) -> str:
        """Format arguments for display in confirmation prompt."""
```

### Phase 3: Streaming Integration

#### 3.1 Enhanced Session Controller
**File**: `src/mochi_coco/controllers/session_controller.py` (modifications)

```python
# Add to existing SessionController class

def process_user_message_with_tools(self, session: ChatSession, model: str,
                                   user_input: str, renderer, 
                                   tools_config: ToolConfig,
                                   available_tools: List[Tool],
                                   available_functions: Dict[str, Callable]) -> MessageProcessResult:
    """Process a regular user message with tool support."""
    
    # Add user message to session
    session.add_user_message(content=user_input)
    
    # Get messages for API and stream response with tools
    messages = session.get_messages_for_api()
    
    # Pass tools to chat stream if enabled
    chat_tools = available_tools if tools_config.enabled else None
    text_stream = self.client.chat_stream(model, messages, tools=chat_tools)
    
    # Use tool-aware renderer
    final_chunk = renderer.render_streaming_response_with_tools(
        text_stream, available_functions, tools_config
    )
    
    if final_chunk:
        session.add_message(chunk=final_chunk)
        return MessageProcessResult(True, final_chunk)
    else:
        return MessageProcessResult(False, None, "No response received")
```

#### 3.2 Tool-Aware Renderer
**File**: `src/mochi_coco/rendering/tool_aware_renderer.py`

```python
from typing import Iterator, Dict, Callable, List, Optional
from ollama import ChatResponse
from ..tools.execution_service import ToolExecutionService
from ..ui.tool_confirmation_ui import ToolConfirmationUI

class ToolAwareRenderer:
    """Enhanced renderer that handles tool calls during streaming."""
    
    def __init__(self, base_renderer, tool_execution_service: ToolExecutionService,
                 confirmation_ui: ToolConfirmationUI):
        self.base_renderer = base_renderer
        self.tool_execution_service = tool_execution_service
        self.confirmation_ui = confirmation_ui
        
    def render_streaming_response_with_tools(self, text_chunks: Iterator[ChatResponse],
                                           available_functions: Dict[str, Callable],
                                           tools_enabled: bool) -> Optional[ChatResponse]:
        """
        Render streaming response handling tool calls.
        
        This method:
        1. Streams text content normally
        2. Detects tool calls and pauses streaming
        3. Prompts user for confirmation
        4. Executes approved tools
        5. Continues streaming with tool results
        """
        
    def _handle_tool_calls(self, chunk: ChatResponse, 
                          available_functions: Dict[str, Callable]) -> List[Dict]:
        """Handle tool calls in a streaming chunk."""
        
    def _create_tool_response_message(self, tool_name: str, result: str) -> Dict:
        """Create a tool response message for the conversation."""
```

#### 3.3 Enhanced Chat Flow
**File**: `src/mochi_coco/chat_controller.py` (modifications)

```python
# Modifications to existing ChatController

def __init__(self, ...):
    # ... existing initialization ...
    
    # Add tool services
    self.tool_discovery_service = ToolDiscoveryService()
    self.tool_schema_service = ToolSchemaService()
    self.tool_execution_service = None  # Initialized when tools are loaded
    self.tool_confirmation_ui = ToolConfirmationUI()
    
    # Tool state
    self.available_tools = {}
    self.tool_groups = {}
    self.current_tools_config = ToolConfig()

def _run_chat_loop(self, session, model):
    """Enhanced chat loop with tool support."""
    
    # Load tools if directory exists
    self._initialize_tools_if_available()
    
    # Existing chat loop with tool integration
    # ... existing code ...
    
def _initialize_tools_if_available(self):
    """Initialize tools if tools directory exists."""
    
def _process_regular_message_with_tools(self, session, model, user_input):
    """Process message with potential tool calls."""
```

### Phase 4: Session Persistence & UI Polish

#### 4.1 Enhanced Message Types
**File**: `src/mochi_coco/chat/session.py` (modifications)

```python
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

@dataclass  
class ToolResponseMessage:
    """A message representing a tool's response."""
    role: str = "tool"
    tool_name: str = ""
    content: str = ""
    message_id: Optional[str] = None
    timestamp: Optional[str] = None

# Add methods to ChatSession class
def add_tool_call_message(self, tool_calls: List[Dict], model: str, **kwargs):
    """Add a tool call message to the session."""
    
def add_tool_response_message(self, tool_name: str, content: str, **kwargs):
    """Add a tool response message to the session."""
```

#### 4.2 Enhanced Menu System
**File**: `src/mochi_coco/ui/menu_display.py` (modifications)

```python
def display_command_menu(self, has_system_prompts: bool = False, 
                        has_tools: bool = False, tools_enabled: bool = False) -> None:
    """Enhanced command menu with tool options."""
    
    commands = [
        ("1", "💬 Switch Sessions", "Change to different chat session"),
        ("2", "🤖 Change Model", "Select a different AI model"),
        ("3", "📝 Toggle Markdown", "Enable/disable markdown rendering"),
        ("4", "🤔 Toggle Thinking", "Show/hide thinking blocks")
    ]
    
    if has_tools:
        tool_status = "enabled" if tools_enabled else "disabled"
        commands.append(("5", "🛠️ Toggle Tools", f"Tool calling is {tool_status}"))
        commands.append(("6", "📂 Change Tools", "Select different tools/groups"))
        
    if has_system_prompts:
        next_num = "7" if has_tools else "5"
        commands.append((next_num, "🔧 Change System", "Select different system prompt"))
```

#### 4.3 Enhanced Command Processor
**File**: `src/mochi_coco/commands/command_processor.py` (modifications)

```python
def process_command(self, user_input: str, session: "ChatSession", model: str) -> CommandResult:
    """Enhanced command processing with tool commands."""
    
    # ... existing commands ...
    
    # Tool commands
    if command == "/tools":
        return self._handle_tools_command(session)
    
def _handle_tools_command(self, session: "ChatSession") -> CommandResult:
    """Handle the /tools command."""
    
def _handle_tools_toggle_command(self, session: "ChatSession") -> CommandResult:
    """Handle toggling tool calling on/off."""
    
def _handle_tools_selection_command(self, session: "ChatSession") -> CommandResult:
    """Handle changing selected tools."""
```

### Phase 5: Testing & Examples

#### 5.1 Unit Tests
**Files**: `tests/test_tools/`

```
tests/test_tools/
├── test_discovery_service.py
├── test_schema_service.py  
├── test_execution_service.py
├── test_tool_aware_renderer.py
└── fixtures/
    └── sample_tools/
        ├── __init__.py
        └── sample_tools.py
```

#### 5.2 Integration Tests
**File**: `tests/integration/test_tool_integration.py`

```python
class TestToolIntegration:
    """Integration tests for complete tool workflow."""
    
    def test_tool_discovery_and_selection_flow(self):
        """Test complete tool discovery and selection."""
        
    def test_tool_execution_during_chat(self):
        """Test tool execution in chat context."""
        
    def test_tool_persistence_in_sessions(self):
        """Test tool calls are saved and loaded correctly."""
```

#### 5.3 Example Tools
**Directory**: `tool_examples/`

```python
# tool_examples/__init__.py
from .file_operations import read_file, edit_file, list_directory
from .system_commands import run_command, get_system_info
from .web_requests import fetch_url

__all__ = [
    "read_file", "edit_file", "list_directory",
    "run_command", "get_system_info", "fetch_url"
]

__file_operations__ = ["read_file", "edit_file", "list_directory"]
__system__ = ["run_command", "get_system_info"]
__web__ = ["fetch_url"]
```

## Migration Strategy

### Backward Compatibility
- All existing functionality remains unchanged
- Tools are optional and don't affect non-tool users
- Session files remain compatible

### Feature Flags
- `MOCHI_TOOLS_ENABLED` environment variable
- Graceful degradation when tools directory missing
- Clear error messages for tool-related issues

### Rollout Plan
1. **Alpha Release**: Core functionality with basic tools
2. **Beta Release**: Full feature set with comprehensive testing
3. **Production Release**: Complete feature with documentation

## Error Handling Strategy

### Discovery Errors
- Missing tools directory: Continue without tools
- Invalid `__init__.py`: Log warning, continue without tools
- Import errors: Skip problematic tools, continue with others

### Execution Errors
- Tool function errors: Return error as tool response
- Timeout errors: Cancel tool, return timeout message
- Permission errors: Clear user-friendly error messages

### Recovery Mechanisms
- Fallback to non-tool mode on critical errors
- Session integrity maintained regardless of tool errors
- Clear user feedback for all error states

## Performance Considerations

### Tool Loading
- Lazy loading of tool modules
- Caching of converted tool schemas
- Efficient tool discovery scanning

### Execution Performance
- Minimal overhead for non-tool sessions
- Efficient tool call detection in streaming
- Optimized confirmation UI rendering

### Memory Management
- Cleanup of tool execution contexts
- Efficient storage of tool call history
- Garbage collection of unused tool references

## Dependencies

### New Dependencies
- No new external dependencies required
- Leverages existing ollama-python tool functionality
- Uses existing Rich UI components

### Version Compatibility
- Python 3.10+ (existing requirement)
- ollama-python 0.5.3+ (existing requirement)
- Compatible with all existing dependencies

## Documentation Plan

### User Documentation
- README updates with tool examples
- Tool creation guide
- Security considerations
- Troubleshooting guide

### Developer Documentation
- Architecture overview
- API documentation
- Contributing guidelines for tools
- Testing procedures

## Future Enhancements

### Phase 2 Features (Post-MVP)
- Tool marketplace/sharing
- Advanced security sandboxing  
- Tool performance analytics
- Auto-approval for trusted tools
- Tool dependency management
- Custom tool directories via config