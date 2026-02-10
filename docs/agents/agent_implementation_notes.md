# Agent Implementation Notes

This document provides **technical guidance** for implementing the agent feature in mochi-coco. It highlights reusable components, integration points, and caveats based on the current architecture and the agent specs.

---

## 1. Reuse Existing Components

### 1.1 Tool discovery + schema conversion
- Reuse the existing **tool discovery pipeline** to load agent tools from `<agent_name>.py`/`__init__.py`.
- Reuse the existing **schema conversion** service to build the tool schema for agent tools.
- The **`agent` tool** itself should be injected into the tool list only when enabled agents exist.

### 1.2 Tool execution pipeline
- Keep the existing **tool execution policy** (confirmation flow) and **tool execution history**.
- The agent tool execution should use the same confirmation rules as normal tools.

### 1.3 Session persistence & message schema
- Agent chats should reuse the **existing ChatSession JSON schema**:
  - `metadata`
  - `messages`
  - `tool_calls`
  - `tool_name` on tool responses
- This allows reusing serialization/migration logic.

### 1.4 Context window management
- The agent request flow should reuse the existing context window calculation logic.
- The exact same config fields can be stored in agent chat metadata.

---

## 2. Avoid Duplicating Logic

### 2.1 Rendering & tool call handling
- Do **not** reimplement tool-call streaming logic.
- Use the existing tool-call pipeline (or adapt it) so that tool calls are captured, executed, and appended to agent chat history in the same format.

### 2.2 Message storage formats
- Do **not** introduce a new message schema for agent chats.
- Use the same `tool_calls` field shape and `tool` role responses.

---

## 3. Key Integration Points

### 3.1 `/agents` menu
- Add a `/agents` command in the menu (mirrors `/tools` selection flow).
- Only show/enable this menu if `./agents` exists.
- Store enabled agents in session metadata.
- Agent selection is **independent** from the tools feature (no tools toggle required).
- When the enabled agent list changes, **invalidate tool schema cache**.

### 3.2 Agent discovery service
- Add an `AgentDiscoveryService` that:
  - Only runs if `./agents` exists
  - Scans `./agents/*/` for agent subfolders
  - Parses `SKILL.md` for `model`, `description`, and prompt
  - Loads tools from `<agent_name>.py` + `__init__.py`
  - Does **not** support tool groups for agents (no `__group__` handling)

### 3.3 Dynamic `agent` tool docstring
- Build the docstring at schema conversion time.
- Include enabled agent names + descriptions.
- Ensure caching is invalidated when enabled agents or descriptions change.

---

## 4. Agent Execution Flow (Loop)

### 4.1 Two-phase flow
- **Planning request**: no tools, ephemeral planning prompt, save response.
- **Execution request(s)**: tools allowed, ephemeral execution prompt, loop on tool calls.

### 4.2 Loop stop condition
- Stop when the agent returns a response **without tool calls**.
- When the loop ends, return **plain text** that begins with `Session ID: <id>`.
- The output must include **all agent messages starting from the last LLM instruction**, plus **all tool calls and tool responses** from that point through the final response.
- Agent sessions are **not** listed in the UI session list.

---

## 5. Prompt Templates (Ephemeral)

Use the two files:
- `docs/agents/agent_prompt_planning.md`
- `docs/agents/agent_prompt_execution.md`

These prompts should be appended to the API request but **not persisted** in agent chat history.

---

## 6. Error Handling

### 6.1 Missing model
- If the model in `SKILL.md` is unavailable, use the current session model.
- Return the Ollama error information in the `agent` tool response.

### 6.2 Missing or invalid agent
- If the requested agent is not enabled or not found, return a clear tool error.
- Do not crash or create a broken session file.

---

## 7. File/Folder Locations

- Agents: `./agents/<agent_name>/`
- Agent chats: `./agents/agent_chats/`
- Specs: `docs/agents/agents_spec.md`

---

## 8. Recommended Order of Implementation

1. Add discovery + parsing of `SKILL.md`
2. Add agent selection `/agents` menu and session storage
3. Inject `agent` tool with dynamic docstring
4. Implement agent chat persistence in `agent_chats/`
5. Implement planning + execution loop
6. Integrate tool-call handling + continuation
7. Add error handling + cache invalidation

---

## 9. File-by-File Implementation Plan

This plan lists **new files** to add and **existing files** to modify, with the intended changes.

### 9.1 New files to create

1. `src/mochi_coco/agents/__init__.py`
   - Export agent services and types.
   - Mirror the structure used in `src/mochi_coco/tools/__init__.py`.

2. `src/mochi_coco/agents/discovery_service.py`
   - Discover agents under `./agents/<agent_name>/`.
   - Parse `SKILL.md` for `model`, `description`, and system prompt.
   - Load agent tool functions from `<agent_name>.py` + `__init__.py`.
   - Return a dictionary of agent definitions.

3. `src/mochi_coco/agents/config.py`
   - Define `AgentSettings` (enabled agents, optional selection metadata).
   - Add serialization helpers similar to `ToolSettings`.

4. `src/mochi_coco/agents/execution_service.py`
   - Execute the `agent` tool:
     - Create or load agent chat session in `./agents/agent_chats/`.
     - Replace system prompt from `SKILL.md`.
     - Run planning request (no tools) using `agent_prompt_planning.md`.
     - Run execution requests (tools allowed) using `agent_prompt_execution.md`.
     - Stop when agent responds without tool calls.
   - Return the final agent output to the caller.

5. `src/mochi_coco/agents/prompt_loader.py` (optional helper)
   - Load prompt templates from:
     - `docs/agents/agent_prompt_planning.md`
     - `docs/agents/agent_prompt_execution.md`

### 9.2 Existing files to modify

1. `src/mochi_coco/chat/session.py`
   - Extend `SessionMetadata` to include `agent_settings`.
   - Add migration logic for a new format version.
   - Serialize/deserialize `agent_settings`.

2. `src/mochi_coco/commands/command_processor.py`
   - Add `/agents` menu similar to `/tools`.
   - Persist enabled agents to session metadata.
   - Invalidate tool schema cache after selection changes.

3. `src/mochi_coco/chat_controller.py`
   - During tool context preparation:
     - Load enabled agents.
     - Inject a single `agent` tool with dynamic docstring.
     - Provide access to agent execution service.

4. `src/mochi_coco/tools/schema_service.py`
   - Support dynamic docstring injection for the `agent` tool.
   - Ensure cache invalidation when enabled agents change.

5. `src/mochi_coco/rendering/tool_aware_renderer.py`
   - Allow the `agent` tool call to be routed to the agent execution service.

6. `src/mochi_coco/ollama/client.py` (if needed)
   - Ensure error propagation for missing models.
   - Return error details in the `agent` tool response.

---

## 10. Test Considerations

- Enable/disable agents and ensure docstring updates correctly.
- Verify the agent session JSON format matches normal chat sessions.
- Ensure the loop stops when no tool calls exist.
- Confirm tool calls and tool responses are appended correctly.

---

## 11. Summary

The agent feature can be implemented by **reusing existing tool, session, and context-window components** and adding a thin orchestration layer for agent discovery, selection, and the two-phase execution loop.