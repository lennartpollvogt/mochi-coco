# Agent Feature Specifications

This document defines the **Agent** feature for mochi-coco. Agents are **an addition to tools**, not a replacement. The agent feature itself is exposed as a **tool** to the main LLM **only if** at least one valid agent exists in the `./agents` directory.

---

## 1. Goals

1. Provide specialized “agent” capabilities that the main LLM can call as a tool.
2. Avoid overwhelming the main LLM with too many tools by delegating tasks to agents.
3. Maintain full compatibility with the existing tools system, session storage, and context-window management.

---

## 2. Directory Structure

Agents are defined in the project root under:

```
./agents/<agent_name>/
```

Each agent directory contains:

- `SKILL.md` (required)
- `<agent_name>.py` (required)
- `__init__.py` (required)

---

## 3. SKILL.md Format

The `SKILL.md` file defines the agent’s metadata and system prompt:

```markdown
---
model: <model_name>
description: <agent_description>
---

<System Prompt>
```

### Notes
- `model` is optional. If the given model does not exist, the **current user-LLM session model** is used as fallback, and the `agent` tool returns the Ollama error information to the caller.
- The system prompt is the **entire body** after the frontmatter.
- The description is used to help the main LLM choose the right agent.

---

## 4. Agent Tools

Each agent can expose its own tools via `<agent_name>.py` and `__init__.py`.

The agent tool rules follow the existing tools feature:
- Type hints required
- Docstrings required
- Exported in `__all__`

---

## 5. Discovery & Exposure

### 5.1 Discovery
An agent is considered valid if:
- `SKILL.md` exists and parses successfully
- `<agent_name>.py` exists
- `__init__.py` exists and exports at least one tool

### 5.2 Exposure
Agents are enabled/disabled via a `/agents` menu and stored in session metadata.
The **agent tool** is exposed to the main LLM only if **at least one valid agent is enabled**.
Only enabled agents are visible to the LLM and accepted by the `agent` tool.

---

## 6. Agent Invocation as Tool

An agent is invoked by the main LLM **as a tool call**.

### 6.1 Tool Call Interface
A **single tool** named `agent` is exposed to the main LLM session. The agent to use is passed as an argument.

- Tool name: `agent`
- Parameters:
  - `agent: string` (must be one of the enabled agents)
  - `instruction: string`
  - `session_id: string` (optional, to continue an existing agent session)

### 6.2 Enabled Agents Visibility (Dynamic Docstring)
The `agent` tool uses a **dynamic docstring** that is generated at tool-schema conversion time. The docstring lists:

- all **enabled agents**
- each agent’s **description** from `SKILL.md`

This allows the main LLM to see which agents exist and what they can do.

**Cache note:** Invalidate the tool-schema cache whenever enabled agents change (e.g., `/agents` selection or reload) or when `SKILL.md` descriptions change. Alternatively, include a hash of the enabled-agent list in the cache key.

### 6.3 Role Assignment
Inside agent chats:
- The **calling LLM** has role: `user`
- The **agent** has role: `assistant`

---

## 7. Agent Chat Sessions

### 7.1 Storage
Each agent chat is stored as JSON in:

```
./agents/agent_chats/
```

The agent chat format reuses the existing `ChatSession` JSON schema (metadata, messages, tool_calls, and tool responses).

### 7.2 Session ID
Each agent chat gets its own `session_id` (same style as normal sessions).

### 7.3 Continuation
The main LLM can continue an agent session by providing the `session_id` in a tool call.

---

## 8. System Prompt Refresh

Each time an agent is called:
- The system prompt in the agent session history is **replaced** by the latest content of `SKILL.md`.
- This ensures:
  - Updated system prompts take effect immediately
  - Updated model selection takes effect immediately

---

## 9. Tool Calls in Agent Chats

Agent tool calls and their responses must be stored **exactly like** in user-LLM chats, including:

- `tool_calls` on assistant messages
- `tool` role responses with `tool_name`
- The same format as existing `ChatSession` storage

---

## 10. Context Window Management

Agent sessions must use **the same context window management logic** as user-LLM sessions.

---

## 11. Execution Policy

Agent execution respects the same tool confirmation policy as the tools system:
- Always confirm
- Never confirm
- Confirm destructive (future)

---

## 12. Looping & Completion (Planning + Execution Flow)

The agent runs in a **two-phase loop**: a **planning request** followed by **execution requests**. The loop continues until the agent makes no tool calls and responds in text.
Ephemeral planning and execution prompts are loaded from `docs/agents/agent_prompt_planning.md` and `docs/agents/agent_prompt_execution.md` (not persisted to chat history) so they can be adjusted without code changes.

### Phase 1: Planning Request (no tools)
1. Create a JSON file for the agent chat with a new `session_id` (or load if continuing).
2. Add **system prompt** from `SKILL.md` and the **LLM’s instruction** as a `user` message to the agent chat history.
3. Prepare the first request:
   - Load chat history from the agent session file.
   - Append an **additional, ephemeral `user` message** instructing the agent to plan next steps and **not use tools**.
   - Do **not** provide tools for this request.
4. Save the agent’s planning response to the agent chat history.

### Phase 2: Task Execution Request(s)
1. Prepare the next request:
   - Load chat history from the agent session file.
   - Provide the agent’s tool list.
   - Append an **ephemeral `user` message** instructing the agent to execute the task or ask for clarification.
2. If the agent produces **tool calls**:
   - Execute tools.
   - Persist tool calls and tool responses in the agent chat history.
   - Send a new request with the updated history + tools.
3. Repeat until the agent finishes or asks for clarification.

### Loop End Conditions
The loop should stop when:
- The agent returns an answer without tool calls.

When the loop ends, the `agent` tool returns **all agent messages starting from the last LLM instruction** up to the **final agent response**.

---

## 13. Summary

Agents extend the current tools model by introducing an **agent tool** callable by the main LLM. Each agent owns:

- its own tools,
- system prompt,
- model selection,
- and its own persistent session history.

The system reuses existing tool execution, session persistence, and context window management.

This provides a consistent, scalable way to delegate tasks while preventing tool overload.
