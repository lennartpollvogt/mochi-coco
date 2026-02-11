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

## 1) Add Agent Module Skeleton ✅ Done

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

## 2) Extend Session Metadata for Agent Settings ✅ Done

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

## 3) Add `/agents` Menu (Enable/Disable Agents) ✅ Done

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

## 4) Dynamic `agent` Tool Injection ✅ Done

**Goal:** Expose a single `agent` tool that lists enabled agents in its docstring.

**New files:**
- `src/mochi_coco/agents/agent_tool.py`
  - `create_agent_tool(enabled_agents)` — factory that generates a fresh `agent` callable with a dynamic docstring listing enabled agent names and descriptions.
  - `get_enabled_agent_definitions(agent_names, all_definitions)` — filters discovered definitions to only valid, enabled agents.
  - `build_agent_tool_for_session(enabled_agent_names, all_definitions)` — convenience entry-point used by `ChatController`.

**Modified files:**
- `src/mochi_coco/chat_controller.py`
  - `_prepare_tool_context()` now checks **both** `has_tools_enabled()` and `has_agents_enabled()`. If only agents are enabled (no regular tools), a tool context is still created with just the `agent` function.
  - Added `_build_agent_tool(session)` helper that discovers agents and calls `build_agent_tool_for_session`.
  - The `agent` function is added to `active_tools` (for the LLM) and `functions` (for `ToolExecutionService`) so it participates in the normal tool pipeline.
  - A default `ToolSettings` is created when only agents are active (no regular tool settings present) to satisfy the tool pipeline.
- `src/mochi_coco/agents/__init__.py`
  - Exports `create_agent_tool`, `build_agent_tool_for_session`, `get_enabled_agent_definitions`.

**Cache invalidation:**
- No changes to `ToolSchemaService` were needed. Each call to `create_agent_tool` returns a **new function object**, so the existing cache key `f"{name}_{id(func)}"` naturally produces a new entry whenever the enabled agents change.

**Notes:**
- The `agent` tool is exposed based on enabled agents, **independent** of `/tools` settings.
- The function currently contains a stub implementation; actual execution routing to `AgentExecutionService` is wired in Step 7.
- Ollama's `convert_function_to_tool` correctly converts the dynamic function to a Tool schema with all three parameters (`agent`, `instruction`, `session_id`) and the agent-listing description.

---

## 5) Agent Chat Persistence ✅ Done

**Goal:** Store agent chat sessions in `./agents/agent_chats/` using the **existing ChatSession JSON format**.

**New files:**
- `src/mochi_coco/agents/execution_service.py`
  - `AgentExecutionService` class with:
    - `create_or_load_session(agent_definition, session_id)` — creates a new `ChatSession` in `./agents/agent_chats/` or loads an existing one by ID.
    - `refresh_system_prompt(session, agent_definition)` — replaces the system message with the latest content from `SKILL.md` on every invocation.
    - `add_user_instruction(session, instruction)` — appends the calling LLM's instruction as a `user` message (spec §6.3: calling LLM = user role).
    - `add_assistant_message(session, response, model)` — persists plain-text agent responses.
    - `add_tool_call_message(session, response, model)` — persists assistant messages containing tool calls in the same format as user-LLM chats (spec §9).
    - `add_tool_response(session, tool_name, result)` — persists tool response messages (role `tool`, with `tool_name`).
    - `build_messages_with_ephemeral(session, ephemeral_user_message)` — builds API message list with an appended ephemeral prompt that is **not** persisted to chat history.
    - `get_agent_tools_as_ollama(agent_definition)` — converts agent tool functions to Ollama `Tool` objects via `ToolSchemaService`.
    - `execute_agent_tool(tool_call, agent_definition, confirm_callback)` — executes a single agent tool call through `ToolExecutionService` with the same confirmation policy as user-LLM tools (spec §11).
    - `format_agent_output(session, instruction_index)` — formats the final output starting with `Session ID: <id>`, including all agent messages, tool calls, and tool responses from the instruction onwards (spec §12).
    - `resolve_agent(agent_name, enabled_agent_names)` — validates that an agent is enabled and discoverable.
    - `execute_agent(...)` — main entry-point (skeleton; loop logic added in Step 6).
- `src/mochi_coco/agents/prompt_loader.py`
  - `load_planning_prompt(path)` — loads and caches the ephemeral planning prompt from `docs/agents/agent_prompt_planning.md` with a hardcoded fallback.
  - `load_execution_prompt(path)` — loads and caches the ephemeral execution prompt from `docs/agents/agent_prompt_execution.md` with a hardcoded fallback.
  - `clear_cache()` — clears the module-level prompt cache for re-reading from disk.

**Modified files:**
- `src/mochi_coco/agents/__init__.py`
  - Exports `AgentExecutionService`, `load_planning_prompt`, `load_execution_prompt` via lazy `__getattr__` to avoid circular imports (`chat.session` → `agents.config` → `agents` → `execution_service` → `chat.session`).

**Verified:**
- Session creation, system prompt refresh, continuation by ID, ephemeral message building, output formatting, persistence on disk, and error handling all tested.
- 122 existing tests pass; 1 pre-existing test failure in `test_e2e_tools.py::test_session_metadata_migration` (expects format_version `1.2` but migration now correctly advances to `1.3` from Step 2).

---

## 6) Planning + Execution Loop ✅ Done

**Goal:** Implement the two-phase loop as described in the spec.

**Implemented in:**
- `src/mochi_coco/agents/execution_service.py` - Complete two-phase loop in `execute_agent()` method
- `src/mochi_coco/rendering/tool_aware_renderer.py` - Agent tool call routing via `_handle_agent_tool_call()`
- `src/mochi_coco/chat_controller.py` - Pass `context_window_service` in tool context
- `src/mochi_coco/controllers/session_controller.py` - Pass `context_window_service` in tool context updates

**Implementation details:**

1. **Planning phase** (no tools):
   - Load or create agent session with `create_or_load_session()`
   - Update system message from `SKILL.md` via `refresh_system_prompt()`
   - Append LLM instruction as `user` message via `add_user_instruction()`
   - Build messages with ephemeral planning prompt (not persisted)
   - Send request via `client.chat_stream()` without tools
   - Collect streaming response and save via `add_assistant_message()`

2. **Execution phase** (tools allowed):
   - Convert agent tools to Ollama Tool schema via `get_agent_tools_as_ollama()`
   - Loop with safety limit (max 10 iterations):
     - Build messages with ephemeral execution prompt (not persisted)
     - Send request via `client.chat_stream()` with agent tools
     - Collect streaming response and detect tool calls
     - If tool calls exist:
       - Save assistant message with tool calls via `add_tool_call_message()`
       - Execute each tool via `execute_agent_tool()` (uses ToolExecutionService)
       - Save tool responses via `add_tool_response()`
       - Continue loop
     - If no tool calls:
       - Save final assistant message
       - Exit loop

3. **Return output:**
   - Format output via `format_agent_output()`:
     - Plain text prefixed with `Session ID: XXXXXXX`
     - Includes all agent messages from last instruction onwards
     - Includes all tool calls and tool responses in that range

4. **Tool routing:**
   - `ToolAwareRenderer._handle_tool_call()` detects tool calls with name `"agent"`
   - Routes agent tool calls to `_handle_agent_tool_call()` which:
     - Extracts arguments (agent, instruction, session_id)
     - Validates required context (session, model, client)
     - Creates `AgentExecutionService` instance
     - Calls `execute_agent()` with confirmation callback
     - Returns `ToolExecutionResult` like any other tool

5. **Context window management:**
   - Agent sessions use the same `ContextWindowService` as regular sessions
   - Context window calculated per request and passed to `client.chat_stream()`
   - Service passed through tool context from `ChatController` → `SessionController` → `ToolAwareRenderer`

6. **Error handling:**
   - Session creation/loading failures return error with session context
   - Planning phase failures return error + session ID for recovery
   - Execution phase failures return error + session ID for recovery
   - Tool execution failures are logged but allow continuation (LLM handles errors)
   - Iteration limit reached adds system note to session

**Notes:**
- Uses the **same context window calculation** as regular sessions
- Uses the same tool execution policy and confirmation UI via callback
- Agent tool calls are indistinguishable from regular tool calls to the main LLM
- All agent responses stored in standard ChatSession format in `./agents/agent_chats/`

---

## 7) Integrate Agent Tool Handling ✅ Done (merged with Step 6)

**Goal:** Route `agent` tool calls through the agent execution service.

**Implemented in:**
- `src/mochi_coco/rendering/tool_aware_renderer.py`

**Changes made:**
- Modified `_handle_tool_call()` to accept optional `tool_context` parameter
- Added detection for tool calls with name `"agent"`
- Routes agent tool calls to new `_handle_agent_tool_call()` method
- All other tools continue through `ToolExecutionService.execute_tool()`

**`_handle_agent_tool_call()` implementation:**
- Extracts arguments: `agent`, `instruction`, `session_id`
- Validates required arguments and tool context
- Gets enabled agents from session via `get_agent_settings()`
- Creates confirmation callback using existing `ToolConfirmationUI`
- Instantiates `AgentExecutionService` with client, tool_settings, context_window_service
- Calls `execute_agent()` and wraps result in `ToolExecutionResult`
- Returns result with same structure as regular tools

**Tool response storage:**
- Agent tool responses stored exactly like other tools:
  - Role `tool`
  - `tool_name="agent"`
  - Content includes final aggregated output starting with `Session ID: XXXXXXX`
- Handled automatically by existing `_add_tool_response_to_session()` in ToolAwareRenderer

**Notes:**
- No changes to general tool call pipeline behavior
- Tool execution history remains intact
- Agent tool calls go through same confirmation flow as regular tools

---

## 8) Error Handling & Fallbacks ✅ Done (implemented inline with Step 6)

**Goal:** Ensure graceful behavior for invalid agents, missing models, or discovery errors.

**Implemented:**
- Invalid/unenabled agents return clear tool error without creating broken session
- Missing SKILL.md models fall back to current session model
- Comprehensive error handling at all phases:
  - Session creation/loading failures
  - Planning phase failures (returns error + session ID)
  - Execution phase failures (returns error + session ID)
  - Tool execution failures (logged, LLM handles errors)
  - Iteration limit (adds system note)
- Exceptions never crash main chat loop (wrapped in try-except)

---

## 9) Cache Invalidation Strategy ✅ Done (via fresh function objects)

**Goal:** Keep the dynamic `agent` tool docstring up to date.

**Implemented:**
- `create_agent_tool()` returns a new function object each time
- Existing cache key uses `id(func)` which naturally produces new entry
- Cache automatically invalidates when:
  - Enabled agent list changes via `/agents` menu
  - Agent definitions change (new discovery)
- No additional cache invalidation logic needed

---

## 10) End-to-End Wiring ✅ Done

**All touchpoints implemented:**

1. **`chat_controller.py`**
   - ✅ Loads enabled agents from session
   - ✅ Injects `agent` tool via `_build_agent_tool()` when agents enabled
   - ✅ Provides `context_window_service` in tool context

2. **`command_processor.py`**
   - ✅ `/agents` menu integrated (Step 3)
   - ✅ Agent selection persisted to session metadata

3. **`tool_aware_renderer.py`**
   - ✅ Routes `agent` tool calls to `AgentExecutionService`
   - ✅ `_handle_agent_tool_call()` method fully implemented

4. **`session_controller.py`**
   - ✅ Passes `context_window_service` through tool context updates

5. **UI**
   - ✅ Agent sessions not listed in standard sessions menu (by design)

---

## 11) Testing Status

### Automated Tests ✅ Complete
- **427 tests passing** (100% pass rate)
- Migration test updated for format_version 1.3
- Agent settings persistence verified
- All existing functionality preserved

### Manual Testing Checklist (Ready for User Testing)

1. **Discovery**
   - [ ] Valid agent with SKILL.md + tools is recognized
   - [ ] Invalid or missing files skip agent with clear logs

2. **/agents menu**
   - [ ] Selecting agents persists in session
   - [ ] Clearing selection removes agent tool exposure
   - [ ] Menu only appears when ./agents exists

3. **Dynamic docstring**
   - [ ] Enabled agent list and descriptions appear in `agent` tool schema
   - [ ] Changes to selection update tool exposure

4. **Planning + Execution**
   - [ ] Planning prompt never persisted to agent chat
   - [ ] Execution prompt never persisted to agent chat
   - [ ] Tool calls are executed and stored correctly
   - [ ] Loop continues on tool calls
   - [ ] Loop stops when no tool calls

5. **Session persistence**
   - [ ] Agent chat stored in `./agents/agent_chats/` with standard schema
   - [ ] Session can be continued with session_id parameter
   - [ ] System prompt refreshed from SKILL.md on each call

6. **Error paths**
   - [ ] Missing/invalid agent returns clear tool error
   - [ ] Missing model falls back to session model
   - [ ] Tool execution errors handled gracefully
   - [ ] Iteration limit prevents infinite loops

7. **Integration**
   - [ ] Agent tool behaves like standard tool to main LLM
   - [ ] Tool confirmation policy respected
   - [ ] Context window management works
   - [ ] Output format includes Session ID

---

## 12) Final Validation ✅ Implementation Complete

**Code Quality:**
- ✅ Agent tool behaves like a standard tool to the main LLM
- ✅ No changes to user-facing chat history beyond normal tool outputs
- ✅ Adheres to existing coding patterns and conventions
- ✅ All type hints correct, no diagnostics errors in modified files
- ✅ Comprehensive logging at all levels
- ✅ Error handling follows project patterns

**Implementation Status:**
- ✅ Steps 1-7: Complete
- ✅ Steps 8-10: Complete (integrated)
- ✅ Step 11: Automated tests passing, manual testing ready
- ✅ Step 12: Code validation complete

**Ready for:** End-to-end testing with real agents by user

**See:** `docs/agents/step6_implementation_summary.md` for detailed implementation notes

---