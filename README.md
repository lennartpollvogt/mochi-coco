# Mochi Coco 🍡

```bash
.-===-.
|[:::]|
`-----´
```

A beautiful, feature-rich CLI chat application for interacting with LLMs via Ollama with streaming responses, session persistence, and markdown rendering.

## Installation

```bash
pip install mochi-coco
```

## Quick Start

1. Make sure you have [Ollama](https://ollama.com) running locally
2. Pull a model: `ollama pull gpt-oss:20b`
3. Start chatting:

```bash
mochi-coco
```

## Features

- 🚀 **Streaming responses** - Real-time chat with immediate feedback
- 💾 **Session persistence** - Your conversations are automatically saved and resumable
- 🎨 **Rich markdown rendering** - Beautiful formatting with syntax highlighting and toggle rendering mid session
- 🔄 **Model switching** - Change models mid-conversation
- ✏️ **Message editing** - Edit previous messages and branch conversations
- 🧠 **Thinking blocks** - Toggle display of model reasoning (when supported)
- 📋 **Session management** - Switch between different chat sessions
- 🎛️ **Interactive menus** - Easy-to-use command interface
- ⚡ **Background summarization** - Automatic conversation summaries

## Commands

While chatting, you can use these commands:

- `/menu` - Open the main menu with all options
  - `/chats` - Switch between existing sessions or create new ones
  - `/models` - Change the current model
  - `/markdown` - Toggle markdown rendering on/off
  - `/thinking` - Toggle thinking blocks display
- `/edit` - Edit a previous message and continue from there
- `/exit` or `/quit` - Exit the application

## Usage

### Basic Chat
```bash
mochi-coco
```

### Custom Ollama Host
```bash
mochi-coco --host http://localhost:11434
```

### Example Session
```markdown
$ mochi-coco

        .-===-.
        |[:::]|
        `-----´

🚀 Welcome to Mochi-Coco Chat!

Previous Sessions:
====================================================================================================
#   Session ID   Model                Preview                                  Messages
----------------------------------------------------------------------------------------------------
1   e6a231af59   gpt-oss:20b          Who was the first Avenger?               8
2   34438dbe67   gpt-oss:20b          Hi                                       4
====================================================================================================

Options:
• Select session (1-2)
• Type 'new' for new chat
• Type '/delete <number>' to delete a session
• Type 'q' to quit
Enter your choice: new
🤖 Model Selection

Available Models:
================================================================================
#   Model Name                     Size (MB)    Family        Max. Cxt Length
--------------------------------------------------------------------------------
1   qwen3:14b                      8846.5       qwen3         40960
2   qwen3:latest                   4983.3       qwen3         40960
3   qwen3:30b                      17697.0      qwen3moe      262144
4   gpt-oss:20b                    13141.8      gptoss        131072
5   llama3.2:latest                1925.8       llama         131072
6   qwen3-coder:latest             17697.0      qwen3moe      262144
7   mistral-small3.2:latest        14474.3      mistral3      131072
================================================================================
ATTENTION: The maximum context length is the supported length of the model but not the actual during the chat session.
Open Ollama application to set default context length!

Select a model (1-7) or 'q' to quit:
Enter your choice: 4

✅ Selected model: gpt-oss:20b

📝 Markdown Rendering
Enable markdown formatting for responses?
This will format code blocks, headers, tables, etc.
Enable markdown? (Y/n): y

🤔 Thinking Block Display
Show model's thinking process in responses?
This will display thinking blocks as formatted quotes.
Show thinking blocks? (y/N): y

💬 New chat started with gpt-oss:20b
Session ID: 6db76b71e1
Markdown rendering is enabled.
Thinking blocks will be displayed.
You:
Hi

Assistant:
Hello! 👋 How can I help you today?

You:
```
