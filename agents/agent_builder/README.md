# Agent Builder Agent

A meta-agent specialized in creating new agents for the mochi-coco system. This agent understands the agent architecture and can generate properly structured agents with comprehensive system prompts and tools.

## Overview

The **agent_builder** agent helps you create new specialized agents by:
- Understanding agent requirements and specifications
- Designing appropriate agent structures
- Writing comprehensive SKILL.md system prompts
- Creating well-documented tool functions
- Setting up proper exports and file structure

## Configuration

- **Model**: `qwen2.5-coder:latest`
- **Location**: `./agents/agent_builder/`
- **Tools**: 5 file operation tools (no CLI execution needed)

## Available Tools

### 1. `read_file(file_path: str, max_lines: int | None = None)`
Reads file contents with line numbers.

### 2. `write_file(file_path: str, text: str)`
Creates new files or overwrites existing ones. Automatically creates parent directories.

### 3. `insert_replace_text(mode: "insert" | "replace", file_path: str, start_line: int, end_line: int | None, new_text: str)`
Precisely insert or replace text at specific line ranges.

### 4. `list_dir(directory_path: str = ".")`
Lists files and directories (excludes common ignore patterns).

### 5. `delete_rename_file(file_path: str, mode: "delete" | "rename", new_name: str | None = None)`
Manages file organization through deletion or renaming.

## What the Agent Knows

The agent_builder has comprehensive knowledge of:

1. **Agent Structure Requirements**:
   - Three required files: `SKILL.md`, `<agent_name>.py`, `__init__.py`
   - Proper directory structure under `./agents/<agent_name>/`

2. **SKILL.md Format**:
   - Frontmatter with `model` and `description` fields
   - System prompt structure and best practices
   - How to write effective agent instructions

3. **Tool Requirements**:
   - Type hints on all parameters and return types
   - Complete docstrings with Args and Returns sections
   - Error handling patterns
   - String return types for LLM compatibility

4. **Design Principles**:
   - Single responsibility per agent
   - Appropriate model selection
   - Safety considerations
   - Quality checklist

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

Select both **agent_builder** and any other agents you want available.

### 2. Request a New Agent

**Example 1: Simple Agent**
```
Use the agent_builder to create a "math_helper" agent that can perform basic arithmetic operations and solve equations.
```

**Example 2: Specialized Agent**
```
I need the agent_builder to create a "data_analyzer" agent with tools for reading CSV files, calculating statistics, and generating summaries.
```

**Example 3: Domain-Specific Agent**
```
Please have the agent_builder create a "docker_manager" agent that can list containers, read logs, and check container status.
```

### 3. Agent Builder Workflow

The agent_builder follows this process:

1. **Understanding Phase**:
   - Asks clarifying questions about the agent's purpose
   - Confirms tool requirements
   - Discusses model selection

2. **Design Phase**:
   - Proposes agent structure
   - Outlines planned tools
   - Suggests system prompt approach

3. **Implementation Phase**:
   - Creates `./agents/<agent_name>/` directory
   - Writes `SKILL.md` with proper frontmatter and comprehensive system prompt
   - Writes `<agent_name>.py` with all tool implementations
   - Writes `__init__.py` with proper exports

4. **Verification Phase**:
   - Confirms all files created
   - Verifies structure is correct
   - Provides usage instructions

## Agent Creation Examples

### Example 1: Research Agent

**Request:**
```
Create a research agent that can search information and compile summaries.
```

**What agent_builder creates:**
- `./agents/researcher/SKILL.md` - System prompt focused on accuracy and citations
- `./agents/researcher/researcher.py` - Tools: search_web, read_url, summarize_text
- `./agents/researcher/__init__.py` - Exports all tools

### Example 2: Code Review Agent

**Request:**
```
I need an agent that reviews code for best practices and security issues.
```

**What agent_builder creates:**
- `./agents/code_reviewer/SKILL.md` - System prompt with code quality guidelines
- `./agents/code_reviewer/code_reviewer.py` - Tools: read_file, analyze_code, check_security
- `./agents/code_reviewer/__init__.py` - Exports all tools

### Example 3: Documentation Agent

**Request:**
```
Create an agent that generates API documentation from code.
```

**What agent_builder creates:**
- `./agents/doc_generator/SKILL.md` - System prompt for documentation standards
- `./agents/doc_generator/doc_generator.py` - Tools: read_file, parse_functions, write_markdown
- `./agents/doc_generator/__init__.py` - Exports all tools

## Best Practices

### When Requesting Agents

1. **Be specific about purpose**: "Create an agent that handles X" rather than "Create an agent"
2. **List desired capabilities**: Mention what tools or operations the agent should support
3. **Mention any constraints**: Safety concerns, resource limits, or restrictions
4. **Specify domain if relevant**: "for Python", "for Docker", "for data analysis"

### What Makes a Good Agent

The agent_builder knows to create agents that are:
- **Focused**: Single, clear purpose
- **Well-documented**: Comprehensive system prompts
- **Safe**: Appropriate boundaries and error handling
- **Practical**: Tools that actually serve the agent's purpose
- **User-friendly**: Clear, helpful responses

## After Creation

Once the agent_builder creates a new agent:

1. **Reload mochi-coco** (or use a command to reload agents if available)
2. **Enable the new agent** via `/agents` menu
3. **Test the agent** with a simple task
4. **Iterate if needed** - ask agent_builder to modify if something isn't right

## Limitations

The agent_builder:
- **Cannot test agents**: It creates files but doesn't verify they work
- **Cannot install dependencies**: If tools need external libraries, you'll need to install them
- **Cannot run the agents**: It only creates the agent structure
- **Follows specifications**: It adheres to mochi-coco's agent system requirements

## Meta-Capability

The agent_builder is itself an agent, which means:
- It can create agents similar to itself
- It can modify existing agents (by reading and rewriting files)
- It can create specialized versions of itself
- It understands its own structure as a reference

This creates interesting possibilities for agent evolution and specialization!

## Technical Details

- **Session Storage**: `./agents/agent_chats/`
- **Created Agents Location**: `./agents/<agent_name>/`
- **Tool Confirmation**: Uses your session's tool execution policy
- **No CLI Access**: Intentionally excludes shell command execution for safety

## Tips

1. **Start simple**: Create basic agents first, then add complexity
2. **Review before using**: Check the generated files to ensure they match your needs
3. **Iterate**: Ask the agent_builder to modify agents if needed
4. **Learn patterns**: Examine created agents to understand agent design
5. **Use as reference**: The coder and agent_builder agents themselves are good examples

## Example Session

```
User: Use the agent_builder to create a simple timer agent that can set and check timers.

LLM: [Calls agent tool]
  agent: agent_builder
  instruction: Create a "timer" agent with tools to set timers, check remaining time, and list active timers

Agent Builder Response:
Session ID: xyz789abc123

I'll create a timer agent with time management capabilities.

[Tool: write_file - SKILL.md]
Created comprehensive system prompt for timer agent:
- Persona: Time management specialist
- Capabilities: Set timers, check status, manage multiple timers
- Model: qwen2.5:latest (general reasoning)

[Tool: write_file - timer.py]
Created 4 tool functions:
- set_timer(name, duration_seconds): Create a new timer
- check_timer(name): Check remaining time
- list_timers(): Show all active timers
- cancel_timer(name): Remove a timer

[Tool: write_file - __init__.py]
Exported all 4 tools in __all__

The timer agent is ready! Enable it with /agents and start managing timers.
```

## See Also

- [Agent Specification](../../docs/agents/agents_spec.md)
- [User Guide](../../docs/agents/user_guide_agents.md)
- [Coder Agent](../coder/README.md) - Another example agent