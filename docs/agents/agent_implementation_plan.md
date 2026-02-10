# Agent Feature Implementation Plan

This plan outlines the ordered, step-by-step implementation for the new agent feature. It is designed to align with the existing tools and session architecture, and to reuse as much of the current pipeline as possible.

---

## 0) Implementation Principles

- **Reuse existing tool discovery, schema conversion, tool execution, session JSON schema, and context-window logic.**
- **Do not introduce new message formats** for agent chats.
- **Use ephemeral prompts** for planning/execution (loaded from existing docs) and **do not persist them** to agent chat history.
- **Expose a single dynamic `agent` tool** only when at least one enabled agent exists.
- **Maintain confirmation policy** consistent with current tool execution rules.
- **Agent feature is independent of tools** (selection via `/agents`, not tied to `/tools`).
- **Only discover agents if `./agents` exists** (no auto-creation).
- **Do not support agent tool groups** (only `__all__` tools).
- **Agent session files are not listed in the UI** (only returned via tool output).
- **Agent tool output is plain text** and must start with `Session ID: XXXXXXX`.

---

## 1) Add Agent Module Skeleton

**Goal:** Introduce a new `agents` module that mirrors the structure of `tools`.

**New files:**
1. `src/mochi_coco/agents/__init__.py`
   - Export discovery, config, execution, and prompt-loader components.

2. `src/mochi_coco/agents/config.py`
   - Define `AgentSettings` with:
     - `enabled_agents: list[str]`
     - Optional selection metadata
   - Add `to_dict()` and `from_dict()` serialization helpers.

3. `src/mochi_coco/agents/discovery_service.py`
   - Discover valid agents under `./agents/<agent_name>/`.
   - Parse `SKILL.md` frontmatter for `model`, `description`, and system prompt content.
   - Load agent tools from `<agent_name>.py` + `__init__.py`.
   - Return an `AgentDefinition` structure that includes:
     - agent name
     - description
     - model (optional)
     - system prompt
     - tool functions (no groups)
     - validity flags and error info

4. `src/mochi_coco/agents/prompt_loader.py` (optional)
   - Load and cache:
     - `docs/agents/agent_prompt_planning.md`
     - `docs/agents/agent_prompt_execution.md`

**Notes:**
- Structure it similar to `tools/discovery_service.py`.
- Use standard logging with consistent patterns.
- Only attempt discovery if `./agents` exists (do not create it).

---

## 2) Extend Session Metadata for Agent Settings

**Goal:** Persist enabled agents in `ChatSession` metadata.

**Modify:**
- `src/mochi_coco/chat/session.py`

**Changes:**
- Add `agent_settings: Optional[AgentSettings]` to `SessionMetadata`.
- Update `format_version` to a new version (e.g., `1.3`).
- Add migration logic:
  - If missing, initialize `agent_settings = None`.
  - If `agent_settings` is a dict, convert via `AgentSettings.from_dict()`.

---

## 3) Add `/agents` Menu (Enable/Disable Agents)

**Goal:** Provide UI to enable/disable agents and store in session metadata.

**Modify:**
- `src/mochi_coco/commands/command_processor.py`
- `src/mochi_coco/ui/menu_display.py` (if needed for new menu copy)

**Changes:**
- Add new command handler `_handle_agents_command`.
- Add `/agents` to the dynamic command map and menu (only when `./agents` exists).
- Implement interaction flow similar to `/tools`:
  - Discover valid agents (via new discovery service).
  - Display list with descriptions.
  - Allow selection of multiple agents.
  - Persist selection in `session.metadata.agent_settings`.
- Invalidate tool schema cache after selection changes.
- Keep this independent of `/tools` (agent selection does not require tools enabled).

**Notes:**
- Reuse UI patterns from `ToolSelectionUI` or create `AgentSelectionUI` if needed.
- Keep selection in `AgentSettings.enabled_agents`.

---

## 4) Dynamic `agent` Tool Injection

**Goal:** Expose a single `agent` tool that lists enabled agents in its docstring.

**Modify:**
- `src/mochi_coco/tools/schema_service.py`
- `src/mochi_coco/chat_controller.py` (tool context injection)
- Potentially `src/mochi_coco/tools/__init__.py` or a dedicated module for the `agent` function.

**Changes:**
- Add a function definition for the `agent` tool (likely in a new module such as `src/mochi_coco/agents/execution_service.py` or a dedicated `agent_tool.py`).
- Build **dynamic docstring** during schema conversion to include:
  - enabled agent names
  - descriptions from `SKILL.md`
- Ensure cache invalidation when enabled agent list or descriptions change.

**Notes:**
- If schema conversion needs dynamic input, add a hook or wrapper in `ToolSchemaService` to accept a docstring override or a unique cache key hash.
- The `agent` tool should be exposed based on enabled agents, not on `/tools` settings.

---

## 5) Agent Chat Persistence

**Goal:** Store agent chat sessions in `./agents/agent_chats/` using the **existing ChatSession JSON format**.

**Add:**
- `src/mochi_coco/agents/execution_service.py`

**Changes:**
- Implement loading/creating `ChatSession` for agent chats with:
  - `sessions_dir=./agents/agent_chats/`
  - `session_id` from tool input (optional)
- Ensure the system prompt is **refreshed from SKILL.md** each invocation:
  - Replace the system message in the agent session.

---

## 6) Planning + Execution Loop

**Goal:** Implement the two-phase loop as described in the spec.

**In `AgentExecutionService`:**
1. **Planning phase** (no tools):
   - Load or create agent session.
   - Update system message from `SKILL.md`.
   - Append LLM instruction as `user` message.
   - Send request with ephemeral planning prompt appended.
   - Save assistant response to agent chat.

2. **Execution phase** (tools allowed):
   - Send request with ephemeral execution prompt appended.
   - If tool calls exist:
     - Execute via existing tool pipeline.
     - Append tool calls and tool responses to agent chat.
     - Repeat execution request.
   - Stop when assistant returns **no tool calls**.

3. **Return output:**
   - Aggregate messages from **the last instruction** through final assistant response, including any tool calls and tool responses in that range.
   - Return as plain text, prefixed with `Session ID: XXXXXXX` on the first line.

**Notes:**
- Use the **same context window calculation** as regular sessions.
- Use the same tool execution policy and confirmation UI.

---

## 7) Integrate Agent Tool Handling

**Goal:** Route `agent` tool calls through the agent execution service.

**Modify:**
- `src/mochi_coco/rendering/tool_aware_renderer.py`

**Changes:**
- Detect tool call with name `agent`.
- Instead of running `ToolExecutionService.execute_tool`, invoke `AgentExecutionService.execute_agent(...)`.
- Ensure the tool response is stored exactly like other tools:
  - Role `tool`
  - `tool_name="agent"`
  - Content includes final aggregated output or error.

**Notes:**
- Do **not** change the general tool call pipeline behavior.
- Keep tool execution history intact.

---

## 8) Error Handling & Fallbacks

**Goal:** Ensure graceful behavior for invalid agents, missing models, or discovery errors.

**Handling:**
- If requested agent is invalid or not enabled:
  - Return a clear tool error.
  - Do not create a broken agent session file.
- If SKILL.md model does not exist:
  - Fall back to current session model.
  - Return Ollama error details in tool output.
- Ensure exceptions never crash the main chat loop.

---

## 9) Cache Invalidation Strategy

**Goal:** Keep the dynamic `agent` tool docstring up to date.

**Plan:**
- Invalidate tool schema cache:
  - When enabled agent list changes (`/agents`).
  - When `SKILL.md` description changes (hash in cache key or explicit invalidation).
- Optionally include a hash of enabled agents + descriptions in schema cache keys.

---

## 10) End-to-End Wiring

**Touchpoints:**
- `chat_controller.py`
  - When preparing tool context:
    - Load enabled agents.
    - Inject `agent` tool if enabled agents exist.
    - Provide agent execution service in tool context.
- `command_processor.py`
  - Add `/agents` and integrate menu display.
- `tool_aware_renderer.py`
  - Route `agent` tool calls to agent execution service.
- UI
  - Do not list agent sessions in the standard sessions menu.

---

## 11) Testing Checklist (Manual)

1. **Discovery**
   - Valid agent with SKILL.md + tools is recognized.
   - Invalid or missing files skip agent with clear logs.

2. **/agents menu**
   - Selecting agents persists in session.
   - Clearing selection removes agent tool exposure.

3. **Dynamic docstring**
   - Enabled agent list and descriptions appear in `agent` tool schema.
   - Cache invalidation works after changing selection.

4. **Planning + Execution**
   - Planning prompt never persisted.
   - Execution prompt never persisted.
   - Tool calls are executed and stored correctly.

5. **Loop stop**
   - Stops when assistant returns no tool calls.

6. **Session persistence**
   - Agent chat is stored in `./agents/agent_chats/` with standard schema.

7. **Error paths**
   - Missing agent / invalid agent returns clear tool error.
   - Missing model falls back and returns Ollama error detail.

---

## 12) Final Validation

- Confirm agent tool behaves like a standard tool to the main LLM.
- Confirm no changes to user-facing chat history beyond normal tool outputs.
- Confirm adherence to existing coding patterns.

---