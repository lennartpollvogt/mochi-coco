# System Prompts User Guide

## Quick Start

1. Create a `./system_prompts` directory in your project
2. Add `.txt` or `.md` files with your system prompts
3. Start mochi-coco and create a new chat session
4. Choose a system prompt during session creation, or
5. Use `/system` command to change the system prompt during a chat session

## What Are System Prompts?

System prompts are instructions that define the AI's role, personality, and behavior for the entire conversation. They set the context and guidelines that the AI follows when responding to your messages.

### Examples of System Prompts

**Coding Assistant (`coding_assistant.txt`)**
```
You are an expert software engineer with deep knowledge of multiple programming languages, frameworks, and best practices. Your role is to:

- Help write clean, efficient, and well-documented code
- Provide code reviews and suggestions for improvement
- Explain complex programming concepts clearly
- Debug issues and suggest solutions
- Follow software engineering best practices

Always provide working code examples and explain your reasoning.
```

**Creative Writer (`creative_writer.md`)**
```markdown
# Creative Writing Assistant

You are a creative writing companion specializing in:
- Fiction writing and storytelling
- Poetry and creative expression
- Character development
- Plot structure and narrative flow
- Writing style and voice development

Help users craft engaging stories, develop characters, and improve their creative writing skills.
```

**Data Analyst (`data_analyst.txt`)**
```
You are a data analysis expert with expertise in statistics, data visualization, and insights generation. Your responsibilities:

- Analyze datasets and identify patterns
- Create clear data visualizations and reports
- Explain statistical concepts in simple terms
- Suggest appropriate analysis methods
- Help interpret results and findings

Focus on actionable insights and clear explanations.
```

## Setting Up System Prompts

### 1. Create the Directory Structure

In your project directory, create a `system_prompts` folder:

```
your-project/
├── system_prompts/
│   ├── coding_assistant.txt
│   ├── creative_writer.md
│   ├── data_analyst.txt
│   └── researcher.txt
└── (other files...)
```

### 2. Supported File Types

- **`.txt`** - Plain text files
- **`.md`** - Markdown files (for formatted prompts)

## Using System Prompts

### During Session Creation

When creating a new chat session, you'll be prompted to select a system prompt:

```
╭─ 🔧 System Prompts ──────────────────────────────────────────────────────────────────────╮
│ ╭─────┬─────────────────┬─────────────────────────────────────┬────────────╮             │
│ │ #   │ Filename        │ Preview                             │ Word Count │             │
│ ├─────┼─────────────────┼─────────────────────────────────────┼────────────┤             │
│ │ 1   │ AGENTS.md       │ You are a helpful agent             │          5 │             │
│ ╰─────┴─────────────────┴─────────────────────────────────────┴────────────╯             │
│                                                                                          │
│ 💡 Options:                                                                              │
│ • 📝 Select system prompt (1-1)• 🆕 Type 'no' for no system prompt• 🗑️ Type '/delete     │
│ <number>' to delete a system prompt• 👋 Type 'q' to quit                                 │
╰──────────────────────────────────────────────────────────────────────────────────────────╯
Enter your choice:
```

### During Chat Session

#### Using Commands

- **`/system`** - Change or select system prompt
- **`/menu`** - Open chat menu, then select system prompt option

#### System Prompt Selection Menu

```
╭────────╮
│ 🧑 You │
╰────────╯
/system
╭─ 🔧 System Prompts ──────────────────────────────────────────────────────────────────────╮
│ ╭─────┬─────────────────┬─────────────────────────────────────┬────────────╮             │
│ │ #   │ Filename        │ Preview                             │ Word Count │             │
│ ├─────┼─────────────────┼─────────────────────────────────────┼────────────┤             │
│ │ 1   │ AGENTS.md       │ You are a helpful agent             │          5 │             │
│ ╰─────┴─────────────────┴─────────────────────────────────────┴────────────╯             │
│                                                                                          │
│ 💡 Options:                                                                              │
│ • 📝 Select system prompt (1-1)• 🆕 Type 'no' for no system prompt• 🗑️ Type '/delete      │
│ <number>' to delete a system prompt• 👋 Type 'q' to quit                                 │
╰──────────────────────────────────────────────────────────────────────────────────────────╯
Enter your choice:
```
