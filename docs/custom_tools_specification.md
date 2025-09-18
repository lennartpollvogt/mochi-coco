# Custom Tools Feature Specification

## Overview

The Custom Tools feature allows users to provide their own Python functions that can be called by LLMs during chat sessions in mochi-coco. This enables users to extend the capabilities of their AI assistants with domain-specific tools while maintaining security through user confirmation prompts.

## Core Concept

Users place Python files containing tool functions in a `tools/` directory in their terminal's working directory. An `__init__.py` file exports these functions for the CLI application to discover and make available to LLMs that support tool calling.

## Directory Structure

```
project_root/
├── tools/
│   ├── __init__.py          # Tool exports and groupings
│   ├── car_information.py   # Tool implementation files
│   ├── weather.py
│   └── file_operations.py
└── other_files...
```

## Tool Definition Format

### Function Requirements
- Must be Python functions with type hints
- Must have comprehensive docstrings following Google/NumPy style
- Must include `Args:` and `Returns:` sections in docstring
- Should handle errors gracefully and return meaningful messages

### Example Tool Function
```python
def get_car_info(info: Literal["oil_temperature", "fuel_level", "speed", "total_distance", "trip_distance"]) -> str:
    """
    Get information about the car.

    Args:
        info (Literal["oil_temperature", "fuel_level", "speed", "total_distance", "trip_distance"]): The type of information to retrieve.

    Returns:
        str: The requested information about the car.
    """
    if info == "oil_temperature":
        return "Oil temperature is 85°C."
    elif info == "fuel_level":
        return "Fuel level is 75%."
    # ... implementation
```

## Tool Export System

### `__init__.py` Structure
The `__init__.py` file defines tool availability through two mechanisms:

1. **Individual Tools** (`__all__`): Tools available for individual selection
2. **Tool Groups** (`__groupname__`): Related tools grouped by functionality

```python
from .weather import get_current_weather
from .car_information import get_car_info
from .file_operations import read_file, edit_file

# Individual tools available for selection
__all__ = ["get_current_weather", "get_car_info", "read_file", "edit_file"]

# Tool groups for domain-specific functionality
__car_assistant__ = ["get_car_info", "get_current_weather"]
__file_operations__ = ["read_file", "edit_file"]
```

## User Interface

### Tool Selection Menu
When a model with tool capabilities is selected, users are presented with:

```
╭─ 🛠️ Available Tools  ────────────────────────────────────────────────────────────╮
│  Single tools                                                                    │
│ ╭─────┬───────────────────────────┬──────────────────────────────────────╮       │
│ │ #   │ Tool Name                 │ Tool Description                     │       │
│ ├─────┼───────────────────────────┼──────────────────────────────────────┤       │
│ │ 1   │ get_car_info              │ Get information about a car.         │       │
│ │ 2   │ get_current_weather       │ Get weather information for a city.  │       │
│ │ 3   │ read_file                 │ Read contents of a file.             │       │
│ │ 4   │ edit_file                 │ Edit a file's contents.              │       │
│ ╰─────┴───────────────────────────┴──────────────────────────────────────╯       │
│                                                                                  │
│  Tool groups                                                                     │
│ ╭─────┬───────────────────────────┬──────────────────────────────────────╮       │
│ │ #   │ Tool Group                │ Tools Included                       │       │
│ ├─────┼───────────────────────────┼──────────────────────────────────────┤       │
│ │ a   │ car_assistant             │ get_car_info, get_current_weather    │       │
│ │ b   │ file_operations           │ read_file, edit_file                 │       │
│ ╰─────┴───────────────────────────┴──────────────────────────────────────╯       │
│                                                                                  │
│ 💡 Options:                                                                      │
│ • 🔢 Select multiple tools (1-4) by listing them (e.g. 1,3,4)                   │
│ • 📂 Select a tool group by choosing a letter (a, b)                            │
│ • ❌ Type 'none' to choose no tools                                             │
│ • 👋 Type 'q' to quit                                                            │
╰──────────────────────────────────────────────────────────────────────────────────╯
```

### Tool Calling Toggle
Tools can be enabled/disabled via the chat menu, similar to markdown and thinking toggles:

```
╭─ ⚙️ Chat Menu ──────────────────────────────────────────────────────────╮
│ ╭─────┬──────────────────────┬───────────────────────────────────╮      │
│ │ #   │ Command              │ Description                       │      │
│ ├─────┼──────────────────────┼───────────────────────────────────┤      │
│ │ 1   │ 💬 Switch Sessions   │ Change to different chat session  │      │
│ │ 2   │ 🤖 Change Model      │ Select a different AI model       │      │
│ │ 3   │ 📝 Toggle Markdown   │ Enable/disable markdown rendering │      │
│ │ 4   │ 🤔 Toggle Thinking   │ Show/hide thinking blocks         │      │
│ │ 5   │ 🛠️ Tool Confirmation │ Enable/disable tool confirmation  │      │
│ │ 6   │ 📂 Change Tools      │ Select different tools/groups     │      │
│ │ 7   │ 🔧 Change System     │ Select different system prompt    │      │
│ ╰─────┴──────────────────────┴───────────────────────────────────╯      │
╰─────────────────────────────────────────────────────────────────────────╯
```

## User Flow

### Initial Setup Flow
1. User starts `mochi-coco`
2. Application scans for `tools/` directory
3. If found, parses `__init__.py` for tool definitions
4. User selects session (new/existing)
5. General userflow: User selects model -> markdown rendering options -> thinking options -> system prompt options -> summarization options (if model does not support structured outputs)
6. Application checks model capabilities for `tools` support
7. If supported, user is presented with tool selection menu
8. User selects individual tools or tool groups or none
9. Chat session begins with selected tools available if selected

### In-Chat Tool Management
1. User types `/menu` in chat
2. User selects "🛠️ Toggle Tools" to enable/disable tool calling
3. User selects "📂 Change Tools" to modify selected tools
4. Changes take effect immediately for subsequent messages

### Tool Execution Flow
1. User sends message to LLM
2. LLM responds with streaming content and/or tool calls
3. When tool call detected:
   - Streaming pauses
   - User confirmation prompt displayed in case tool confirmation is enabled:
   ```
   ╭─ ⚠️ Tool Execution Confirmation ─────────────────────────────╮
   │ 🛠️ Tool Call Request:                                       │
   │                                                             │
   │ Function: get_current_weather                               │
   │ Arguments: {"city": "London"}                               │
   │                                                             │
   │ Allow execution? [y/N]:                                     │
   ╰─────────────────────────────────────────────────────────────╯
   ```
4. If approved:
   - Tool executes with provided arguments
   - Result added to conversation context
   - Streaming continues with tool result available to LLM
5. If denied:
   - Tool call skipped
   - LLM informed that tool was not available
   - Streaming continues

The user confirmation prompt is displayed when tool confirmation is enabled. In case the tool confirmation is disabled, no prompt for confirmation is displayed to the user and the tool is executed automatically.

## Session Persistence

Tool calls and responses are stored in the session JSON format:

```json
{
  "role": "assistant",
  "content": "",
  "tool_calls": [
    {
      "function": {
        "name": "get_current_weather",
        "arguments": {"city": "London"}
      }
    }
  ],
  "model": "qwen2.5:7b",
  "message_id": "abc123",
  "timestamp": "2025-01-09T10:30:00.000Z"
},
{
  "role": "tool",
  "tool_name": "get_current_weather",
  "content": "Weather in London is sunny, 18°C",
  "message_id": "def456",
  "timestamp": "2025-01-09T10:30:01.000Z"
}
```

Tool settings are stored in the metadata of the session JSON format:

```json
{
  "metadata": {
    "session_id": "bf0c1a78a5",
    "model": "gpt-oss:20b",
    "tools_settings": {
      "tools": ["get_current_weather"], // list of single tools from __all__ variable
      "tool_group": "car_assistant", // based on __car_assistant__ variable
      "confirmation_necessary": true // or false to allow tool usage without user confirmation
    },
    "created_at": "2025-09-17T07:58:37.168192",
    "updated_at": "2025-09-17T07:59:36.715703",
    "message_count": 2,
    "summary": {
      "summary": "The user asked about the first Avenger in the MCU and received a response identifying Captain America as the first official Avenger, recruited by Nick Fury in 2012.",
      "topics": [
        "Avengers",
        "Marvel Cinematic Universe"
      ]
    },
    "summary_model": "llama3.2:latest"
  },
  "messages": []
}
```

IMPORTANT: The user can select several single tools OR one tool group. Having a tools group and single tools is not allowed. Also, having several tool groups is not allowed.

## Model Compatibility

### Capability Detection
The application uses Ollama's model capability detection:
```python
model_info = client.show(model='model-name')
capabilities = model_info.capabilities
tool_support = 'tools' in capabilities
```

### Tool-Capable Models Display
Models are displayed with tool support indication:
```
╭─ Available Models ───────────────────────────────────────────────╮
│ # │ Model Name    │ Size │ Family │ Max Ctx │ Tools │            │
├───┼───────────────┼──────┼────────┼─────────┼───────┤            │
│ 1 │ qwen2.5:7b    │ 4.4G │ qwen2  │ 32768   │ Yes   │            │
│ 2 │ llama3.2:3b   │ 2.0G │ llama  │ 8192    │ No    │            │
╰───┴───────────────┴──────┴────────┴─────────┴───────╯            │
```

## Security Considerations

### User Confirmation
- All tool calls require explicit user approval unless the confirm tool functionality is disabled (see toggle within chat menu)
- Confirmation prompts is part of the user interaction with the application and are not saved to chat history
- Users can deny individual tool calls within a single response

### Error Handling
- Tool execution errors are caught and presented gracefully within the UI and the chat history.
- Failed tools don't crash the application
- Error messages are returned to the LLM as tool responses

### Import Restrictions
Tools run within the same Python environment but with:
- Clear error reporting for import failures
- Graceful handling of missing dependencies

## Example Tools

The application should include example tools in `tool_examples/`:

1. **File Operations**: `read_file`, `edit_file`, `list_directory`
2. **System Commands**: `run_cli_command`, `get_system_info`
4. **Development**: `run_tests`, `check_syntax`, `format_code`

## Configuration

### Tool Discovery Settings
- Default tools directory: `./tools/`
- Configurable via environment variable: `MOCHI_TOOLS_DIR`
- Fallback behavior when no tools found: Continue without tool support

### User Preferences
- Tool confirmation enabled/disabled (persisted per session)
- Selected tools/groups (persisted per session)

## Error States and Handling

### Missing Tools Directory
- Application continues normally
- Tool selection is skipped
- No impact on non-tool-supporting models

### Invalid Tool Definitions
- Malformed `__init__.py`: Skip tool discovery, show warning
- Missing docstrings: Tool excluded from selection, warning logged
- Import errors: Individual tools skipped, errors reported

### Runtime Errors
- Tool execution failures: Error message returned as tool response
- Network timeouts: Graceful degradation with error reporting
- Permission errors: Clear error messages to user
