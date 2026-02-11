# Coder Agent

A specialized coding agent with comprehensive file system operations, code editing, and shell command execution capabilities.

## Overview

The **coder** agent is designed to assist with software development tasks including:
- Reading and writing files
- Editing code with precise line-level control
- Browsing project structure
- Managing files (rename, delete)
- Executing shell commands and scripts

## Configuration

- **Model**: `qwen2.5-coder:latest`
- **Location**: `./agents/coder/`
- **Tools**: 6 specialized tools for file and code operations

## Available Tools

### 1. `read_file(file_path: str, max_lines: int | None = None)`
Reads file contents with line numbers.

**Example use cases:**
- Inspecting code before making changes
- Reviewing configuration files
- Understanding project structure

### 2. `write_file(file_path: str, text: str)`
Creates new files or overwrites existing ones. Automatically creates parent directories.

**Example use cases:**
- Creating new source files
- Writing configuration files
- Generating documentation

### 3. `insert_replace_text(mode: "insert" | "replace", file_path: str, start_line: int, end_line: int | None, new_text: str)`
Precisely insert or replace text at specific line ranges.

**Example use cases:**
- Fixing bugs in existing code
- Adding new functions to a module
- Updating specific sections of files

### 4. `list_dir(directory_path: str = ".")`
Lists files and directories (excludes common ignore patterns).

**Example use cases:**
- Exploring project structure
- Finding files to modify
- Understanding codebase organization

### 5. `delete_rename_file(file_path: str, mode: "delete" | "rename", new_name: str | None = None)`
Manages file organization through deletion or renaming.

**Example use cases:**
- Cleaning up obsolete files
- Reorganizing project structure
- Renaming files to match conventions

### 6. `run_cli_command(command: str)`
Executes shell commands and returns output.

**Example use cases:**
- Running tests
- Building projects
- Installing dependencies
- Checking code with linters

## Usage

### 1. Enable the Agent

Start mochi-coco and use the `/agents` command:

```bash
mochi-coco
```

Then in the chat:
```
/agents
```

Select the **coder** agent from the list.

### 2. Delegate Tasks to the Agent

Use the agent through the main LLM by describing what you want:

**Example 1: Reading and Understanding Code**
```
Can you use the coder agent to explore the src/ directory and explain the project structure?
```

**Example 2: Creating New Files**
```
Please have the coder agent create a new Python module at src/utils/helpers.py with a function to validate email addresses.
```

**Example 3: Fixing Bugs**
```
The coder agent should read src/main.py, find the bug on line 42, and fix it.
```

**Example 4: Running Tests**
```
Ask the coder agent to run pytest and report the results.
```

### 3. Continue Agent Sessions

Agent sessions are automatically tracked. The main LLM can continue previous agent sessions by referencing the Session ID.

## Agent Workflow

The coder agent follows a two-phase workflow:

### Phase 1: Planning
- Receives your instruction
- Analyzes the task
- Plans the approach
- **Does not use tools yet**

### Phase 2: Execution
- Executes the plan using available tools
- Makes multiple tool calls as needed
- Iterates until task is complete
- Returns final results

## Best Practices

### For Code Changes
1. **Always read before editing**: The agent reads files first to understand context
2. **Verify line numbers**: Precise line numbers ensure accurate edits
3. **Test changes**: Consider asking the agent to run tests after modifications

### For File Operations
1. **Check before deleting**: The agent is cautious with destructive operations
2. **Review before committing**: Inspect agent changes before version control
3. **Use relative paths**: Work within project boundaries

### For Shell Commands
1. **Explain commands**: The agent describes what commands do
2. **Start simple**: Begin with safe, read-only commands
3. **Review output**: The agent interprets command results

## Safety Features

- **Confirmation policy**: Respects your tool execution settings
- **Error handling**: Gracefully handles file not found, permissions, etc.
- **Iteration limits**: Prevents infinite loops (max 10 iterations)
- **Clear reporting**: All operations are logged and reported

## Example Session

```
User: Use the coder agent to create a simple calculator module

LLM: [Calls agent tool]
  agent: coder
  instruction: Create a Python module at src/calculator.py with basic arithmetic functions (add, subtract, multiply, divide)

Agent Response:
Session ID: abc123def456

I'll create a calculator module with comprehensive functions and error handling.

[Tool: write_file]
Created src/calculator.py with 4 functions:
- add(a, b): Addition with type checking
- subtract(a, b): Subtraction with type checking
- multiply(a, b): Multiplication with type checking
- divide(a, b): Division with zero check

The module is ready to use with proper docstrings and error handling.
```

## Troubleshooting

### Agent Not Available
- Ensure `./agents/coder/` directory exists
- Check that all three files are present: `SKILL.md`, `coder.py`, `__init__.py`
- Verify the agent is enabled via `/agents` menu

### Tool Execution Fails
- Check file paths are correct (relative to project root)
- Verify permissions for file operations
- Ensure commands are valid for your system

### Model Not Found
- Install the model: `ollama pull qwen2.5-coder:latest`
- Or the agent will fall back to your current session model

## Technical Details

- **Session Storage**: `./agents/agent_chats/`
- **Session Format**: Standard ChatSession JSON
- **Tool Confirmation**: Uses your session's tool execution policy
- **Context Management**: Same as regular chat sessions

## Tips

1. **Be specific**: Clear instructions help the agent work efficiently
2. **Use continuation**: Reference Session IDs to continue complex tasks
3. **Combine tools**: The agent can chain multiple operations
4. **Inspect results**: Ask the agent to verify changes by reading files

## See Also

- [Agent Specification](../../docs/agents/agents_spec.md)
- [User Guide](../../docs/agents/user_guide_agents.md)
- [Implementation Plan](../../docs/agents/agent_implementation_plan.md)