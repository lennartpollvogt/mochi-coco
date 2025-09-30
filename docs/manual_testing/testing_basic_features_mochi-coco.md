# Manual Testing Guide for Mochi-Coco

This document contains comprehensive manual test cases for the mochi-coco chat application, covering all features and user flows.

## Application Startup

### Test Case 1: Basic Application Startup
**Prerequisites:** None
**Steps:**
1. Open terminal in any directory
2. Execute `mochi-coco` command
3. Application starts and attempts to load chat sessions from `chat_sessions` folder

**Expected Results:**
- Application displays welcome message: "🚀 Welcome to Mochi-Coco Chat!"
- Loads existing sessions (if any) or proceeds to no-sessions flow

### Test Case 2: Startup with Existing Sessions
**Prerequisites:** At least one chat session exists in `chat_sessions` folder
**Steps:**
1. Execute `mochi-coco` command
2. Application displays sessions table

**Expected Results:**
- Sessions table displays with columns: `#`, `Session ID`, `Model`, `Preview`, `Messages`
- Options menu shows:
  ```
  Options:
  • Select session (1-n)
  • Type 'new' for new chat
  • Type '/delete <number>' to delete a session
  • Type 'q' to quit
  ```

### Test Case 3: Startup without Existing Sessions
**Prerequisites:** No chat sessions exist in `chat_sessions` folder
**Steps:**
1. Execute `mochi-coco` command

**Expected Results:**
- Message: "No previous sessions found. Starting new chat..."
- Proceeds directly to model selection menu

## Session Management

### Test Case 4: Select Existing Session
**Prerequisites:** Multiple existing sessions
**Steps:**
1. From session selection menu, enter a valid session number
2. Confirm markdown rendering preference (Y/n)
3. If markdown enabled, confirm thinking blocks preference (y/N)

**Expected Results:**
- Session loads successfully
- Chat history displays (if any)
- Message shows: "✅ Loaded session: [session_id] with [model]"
- Chat prompt appears with help text

### Test Case 5: Create New Session
**Prerequisites:** At session selection menu
**Steps:**
1. Type `new` and press enter
2. Models table displays
3. Select a model by number
4. Configure markdown and thinking preferences

**Expected Results:**
- Models table shows columns: `#`, `Model Name`, `Size (MB)`, `Family`, `Max. Ctx Length`
- New session created with selected model
- Message shows: "💬 New chat started with [model]"
- Session ID displayed

### Test Case 6: Delete Session
**Prerequisites:** Multiple existing sessions
**Steps:**
1. Type `/delete <number>` (e.g., `/delete 2`)
2. Confirm deletion when prompted

**Expected Results:**
- Confirmation prompt shows session details
- After confirmation, session deleted
- Sessions list refreshes without deleted session
- Success message: "Session [session_id] deleted successfully!"

### Test Case 7: Invalid Session Selection
**Prerequisites:** Session selection menu with n sessions
**Steps:**
1. Enter invalid number (0, n+1, or non-numeric)

**Expected Results:**
- Error message: "Please enter a number between 1 and n, 'new', '/delete <number>', or 'q'"
- Prompt repeats

### Test Case 8: Quit Application
**Prerequisites:** At any menu
**Steps:**
1. Type `q`, `quit`, or `exit`

**Expected Results:**
- Application exits with message: "Exiting." or similar
- Returns to terminal

## Chat Session Commands

### Test Case 9: Access Menu System
**Prerequisites:** Active chat session
**Steps:**
1. Type `/menu` in chat
2. Menu displays with 4 options

**Expected Results:**
- Command menu table displays:
  ```
  ⚙️  Command Menu
  #   Command         Description
  1   chats          Switch to a different chat session
  2   models         Change the current model
  3   markdown       Toggle markdown rendering
  4   thinking       Toggle thinking blocks display
  ```
- Prompt: "Select an option (1-4) or 'q' to cancel:"

### Test Case 10: Menu - Switch Models
**Prerequisites:** In command menu
**Steps:**
1. Select option `2` (models)
2. Models table displays
3. Select a new model by number

**Expected Results:**
- Models table shows available models
- After selection: "✅ Switched to model: [model_name]"
- Returns to chat session with new model

### Test Case 11: Menu - Switch Chat Sessions
**Prerequisites:** In command menu, multiple sessions exist
**Steps:**
1. Select option `1` (chats)
2. Sessions table displays
3. Select different session or create new one

**Expected Results:**
- Sessions selection menu appears
- Can switch to existing session or create new one
- Preference collection for markdown/thinking
- Returns to selected/new session

### Test Case 12: Menu - Toggle Markdown Rendering
**Prerequisites:** In command menu
**Steps:**
1. Select option `3` (markdown)

**Expected Results:**
- Message: "✅ Markdown rendering enabled/disabled"
- Chat history re-renders in new format
- Returns to chat session

### Test Case 13: Menu - Toggle Thinking Blocks
**Prerequisites:** In command menu, markdown rendering enabled
**Steps:**
1. Select option `4` (thinking)

**Expected Results:**
- Message: "✅ Thinking blocks will be shown/hidden"
- Chat history re-renders with/without thinking blocks
- Returns to chat session

### Test Case 14: Menu - Toggle Thinking (Markdown Disabled)
**Prerequisites:** In command menu, markdown rendering disabled
**Steps:**
1. Select option `4` (thinking)

**Expected Results:**
- Warning: "⚠️ Thinking blocks can only be toggled in markdown mode."
- Instructions to enable markdown first
- Returns to chat session

### Test Case 15: Menu - Cancel Operation
**Prerequisites:** In command menu
**Steps:**
1. Type `q`, `quit`, or `exit`

**Expected Results:**
- Message: "Returning to chat."
- Returns to chat session without changes

### Test Case 16: Menu - Invalid Selection
**Prerequisites:** In command menu
**Steps:**
1. Enter invalid input (5, abc, etc.)

**Expected Results:**
- Error: "Please enter 1, 2, 3, 4, or 'q'"
- Menu redisplays

### Test Case 17: Direct Edit Command
**Prerequisites:** Active chat session with user messages
**Steps:**
1. Type `/edit` in chat

**Expected Results:**
- Edit menu displays with message table
- Shows columns: `#`, `Role`, `Preview`
- Only user messages numbered
- Prompt: "Select a user message (1-n) or 'q' to cancel:"

### Test Case 18: Edit User Message
**Prerequisites:** In edit menu
**Steps:**
1. Select user message number
2. Edit the message content
3. Submit changes

**Expected Results:**
- Original message displays for reference
- Input field pre-filled with original content
- After editing: "Message #n edited successfully!"
- All messages after edited message removed
- LLM automatically responds to edited message
- Chat history re-renders

### Test Case 19: Edit - Cancel Operation
**Prerequisites:** In edit menu or during editing
**Steps:**
1. Type `q` or press Ctrl+C

**Expected Results:**
- Message: "Edit cancelled." or "Operation cancelled."
- Returns to chat session unchanged

### Test Case 20: Edit - No Messages to Edit
**Prerequisites:** Empty chat session
**Steps:**
1. Type `/edit`

**Expected Results:**
- Warning: "⚠️ No user messages to edit in this session."
- Returns to chat session

## Chat Functionality

### Test Case 21: Basic Chat Interaction
**Prerequisites:** Active chat session
**Steps:**
1. Type a message and press enter

**Expected Results:**
- Message displays with "You:" label
- LLM responds with "Assistant:" label
- Conversation saves to session file

### Test Case 22: Exit Commands
**Prerequisites:** Active chat session
**Steps:**
1. Type `/exit`, `/quit`, or `/q`

**Expected Results:**
- Message: "Goodbye."
- Application terminates

### Test Case 23: Empty Input Handling
**Prerequisites:** Active chat session
**Steps:**
1. Press enter without typing anything

**Expected Results:**
- No action taken
- Prompt reappears for next input

### Test Case 24: Keyboard Interrupt
**Prerequisites:** At any prompt
**Steps:**
1. Press Ctrl+C

**Expected Results:**
- Graceful handling with appropriate message
- Returns to previous state or exits application

## Error Handling

### Test Case 25: No Models Available
**Prerequisites:** Ollama server running but no models installed
**Steps:**
1. Try to create new session or switch models

**Expected Results:**
- Error message about no available models
- Instructions to download models first

### Test Case 26: Ollama Server Unavailable
**Prerequisites:** Ollama server not running
**Steps:**
1. Start application or try model operations

**Expected Results:**
- Connection error message
- Guidance on starting Ollama server

### Test Case 27: Model No Longer Available
**Prerequisites:** Session with model that was removed from Ollama
**Steps:**
1. Try to load session with unavailable model

**Expected Results:**
- Warning about unavailable model
- Prompt to select replacement model
- Session updates with new model

### Test Case 28: Invalid File Permissions
**Prerequisites:** No write permissions in working directory
**Steps:**
1. Try to create or save session

**Expected Results:**
- Appropriate error message
- Graceful degradation or alternative path

## Rendering and Display

### Test Case 29: Markdown Rendering Enabled
**Prerequisites:** Chat session with markdown rendering on
**Steps:**
1. Send message that generates formatted response

**Expected Results:**
- Code blocks properly formatted
- Headers styled appropriately
- Tables rendered correctly

### Test Case 30: Thinking Blocks Display
**Prerequisites:** Markdown enabled, thinking blocks on, model that generates thinking
**Steps:**
1. Send message to model that shows thinking process

**Expected Results:**
- Thinking blocks displayed as formatted quotes
- Clear separation from main response

### Test Case 31: Plain Text Rendering
**Prerequisites:** Markdown rendering disabled
**Steps:**
1. Send message that would generate formatted response

**Expected Results:**
- All text displayed as plain text
- No special formatting applied

## Session Persistence

### Test Case 32: Session Auto-Save
**Prerequisites:** Active chat session
**Steps:**
1. Send several messages
2. Check `chat_sessions` folder

**Expected Results:**
- Session file exists with correct session ID
- File contains all messages and metadata
- Updates after each exchange

### Test Case 33: Session Loading
**Prerequisites:** Existing session file
**Steps:**
1. Restart application
2. Select existing session

**Expected Results:**
- All previous messages load correctly
- Session metadata preserved
- Chat history displays properly

### Test Case 34: Cross-Session Data Integrity
**Prerequisites:** Multiple sessions
**Steps:**
1. Switch between sessions
2. Verify message history

**Expected Results:**
- Each session maintains separate history
- No cross-contamination of messages
- Metadata stays consistent

## Performance and Edge Cases

### Test Case 35: Large Session History
**Prerequisites:** Session with many messages (>100)
**Steps:**
1. Load and interact with large session

**Expected Results:**
- Reasonable load times
- Smooth scrolling and display
- No memory issues

### Test Case 36: Long Messages
**Prerequisites:** Active session
**Steps:**
1. Send very long message (>1000 characters)
2. Receive long response

**Expected Results:**
- Messages display properly
- No truncation or display issues
- Proper line wrapping

### Test Case 37: Special Characters and Unicode
**Prerequisites:** Active session
**Steps:**
1. Send messages with emojis, special characters, non-English text

**Expected Results:**
- All characters display correctly
- No encoding issues
- Proper file saving and loading

## Help and User Guidance

### Test Case 38: Help Text Display
**Prerequisites:** New chat session
**Steps:**
1. Observe help text when session starts

**Expected Results:**
- Clear instructions: "Type 'exit' to quit, '/menu' to access settings, or '/edit' to edit messages."
- Current settings status displayed

### Test Case 39: Context-Aware Prompts
**Prerequisites:** Various application states
**Steps:**
1. Navigate through different menus and options

**Expected Results:**
- Prompts clearly indicate available options
- Context-appropriate help text
- Consistent formatting and styling

### Test Case 40: Error Recovery
**Prerequisites:** Various error states
**Steps:**
1. Trigger errors and observe recovery options

**Expected Results:**
- Clear error messages
- Guidance on how to proceed
- Graceful recovery to stable state

## Background Summarization

### Test Case 41: Automatic Summary Generation
**Prerequisites:** Active chat session with background summarization enabled
**Steps:**
1. Start a new chat session
2. Have a conversation with at least 3-4 exchanges (user message + assistant response)
3. Wait 3-5 seconds after the last assistant response
4. Navigate to the `chat_sessions` folder
5. Open the session JSON file for the current session
6. Look for the `summary` field in the metadata section

**Expected Results:**
- Session JSON file contains a `metadata` object
- `metadata.summary` field exists and is not null/empty
- Summary is a concise 1-2 sentence description of the conversation
- `metadata.updated_at` timestamp reflects when summary was generated
- Summary updates automatically after each new assistant response
- No interruption to the main chat experience during summary generation

### Test Case 42: Summary Content Quality and Updates
**Prerequisites:** Active chat session
**Steps:**
1. Start conversation about a specific topic (e.g., "Explain how photosynthesis works")
2. Continue conversation with follow-up questions on the same topic
3. Check summary in session JSON file after 2-3 exchanges
4. Switch to a completely different topic (e.g., "Now tell me about cooking pasta")
5. Continue conversation on new topic for 2-3 exchanges
6. Check updated summary in session JSON file
7. Compare the initial summary with the final summary

**Expected Results:**
- Initial summary accurately reflects the first topic discussed
- Updated summary reflects both topics or focuses on the overall conversation themes
- Summary remains concise (1-2 sentences) even as conversation grows
- Summary content is coherent and meaningful
- Each summary update overwrites the previous one (no accumulation)
- Summary generation happens in background without affecting chat responsiveness
- Timestamps in `updated_at` field change with each summary update