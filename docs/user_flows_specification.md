# User Flows Specification - Summary Model Selection

This document defines the complete user flows for session creation, loading, and switching, with detailed specifications for summary model selection behavior in all scenarios.

## Overview

The application must handle summary model selection consistently across all user flows. A summary model is needed when:
1. The chat model doesn't support structured output for summaries
2. No valid summary model is stored in the session
3. The stored summary model is no longer available or supported

## Core Principles

1. **Consistency**: Summary model selection behavior must be identical across all flows
2. **User Experience**: Summary model selection happens BEFORE session info display
3. **Validation**: Always validate stored summary models for both availability and compatibility
4. **Graceful Degradation**: Handle edge cases without crashing or leaving invalid state

## Model Compatibility

### Unsupported Models (for summaries)
- `gpt-oss:20b`
- `gpt-oss:120b`
- `qwen3:14b`
- `qwen3:30b`

### Supported Models (for summaries)
- `llama3.2:latest`
- `qwen3:latest`
- `mistral-small3.2:latest`
- `qwen3-coder:latest`
- Any other models not in the unsupported list

---

## Flow 1: User Starts Application and Creates New Session

### Main Flow
1. **Application Startup**
   - Welcome message displayed
   - Check for existing sessions

2. **Previous Sessions**
   - **No Previous Sessions Found**
     - Display "No Previous Sessions Found" message
     - Proceed directly to new session creation
   - **Previous Sessions Found**
     - Display list of previous sessions
     - User types in "new" to create new session

3. **Model Selection**
   - Display available models table
   - User selects chat model
   - Model selection confirmed

4. **Preferences Collection**
   - Markdown rendering preference (y/n)
   - Thinking blocks preference (y/n)

5. **System Prompt Selection**
   - Display available system prompts (if any)
   - User selects prompt or chooses "no"

6. **Summary Model Validation & Selection**
   - **IF** chat model supports summaries → Skip summary model selection
   - **IF** chat model doesn't support summaries → Prompt for summary model selection
     - Display info message explaining why summary model is needed
     - Show filtered model table (only supported models)
     - User selects summary model
     - Confirm selection and store in session metadata

7. **Session Setup Complete**
   - Display session info panel with:
     - Session ID
     - Chat model
     - Markdown setting
     - Thinking blocks setting
     - Available commands
   - Start background services
   - Ready for user input

### Edge Cases

#### EC1.1: User Cancels Model Selection
- **When**: User types 'q' during chat model selection
- **Action**: Exit application gracefully

#### EC1.2: User Cancels Summary Model Selection
- **When**: User types 'q' during summary model selection
- **Action**: Turn back to step `1. **Application Startup**`

#### EC1.3: No Models Available
- **When**: No models are installed or available
- **Action**: Display error message and exit

#### EC1.4: No Compatible Summary Models Available
- **When**: Chat model is unsupported but no compatible summary models exist
- **Action**: Display error message, disable summarization, continue with session

#### EC1.5: Network/API Errors During Model Listing
- **When**: Cannot retrieve model list from Ollama
- **Action**: Display error message and retry options

---

## Flow 2: User Starts Application and Loads Previous Session

### Main Flow
1. **Application Startup**
   - Welcome message displayed
   - List existing sessions in table format

2. **Session Selection**
   - User selects session number
   - Load session metadata and messages

3. **Preferences Collection**
   - Markdown rendering preference (y/n)
   - Thinking blocks preference (y/n)

4. **Session Validation & Summary Model Check**
   - Load session metadata (chat model, stored summary model)
   - **Validate Chat Model Availability**:
     - IF chat model no longer available → Prompt for new model selection
   - **Validate Summary Model Requirements**:
     - IF chat model supports summaries → No summary model needed
     - IF chat model doesn't support summaries:
       - **Check Stored Summary Model**:
         - IF no stored summary model → Prompt for selection
         - IF stored summary model exists:
           - Validate model is still installed → If not, prompt for new selection
           - Validate model is still supported → If not, prompt for new selection
           - IF valid → Use stored model

5. **Summary Model Selection** (if needed)
   - Display info message explaining why selection is needed
   - Show filtered model table (only supported models)
   - User selects summary model
   - Update session metadata with new selection

6. **Session Setup Complete**
   - Display session info panel
   - Display chat history (if any)
   - Start background services
   - Ready for user input

### Edge Cases

#### EC2.1: User Cancels Session Selection
- **When**: User types 'q' during session selection
- **Action**: Exit application gracefully

#### EC2.2: Selected Session File Corrupted
- **When**: Session JSON is malformed or unreadable
- **Action**: Display error, remove from list, ask user to select another

#### EC2.3: Chat Model No Longer Available
- **When**: Session's chat model is no longer installed
- **Action**: Display warning, prompt for new model selection, update session

#### EC2.4: Stored Summary Model Invalid
- **When**: Session has summary model that's unsupported (e.g., `gpt-oss:20b`)
- **Action**: Display warning, reset stored model, prompt for new selection

#### EC2.5: Both Chat and Summary Models Invalid
- **When**: Both models are no longer available/supported
- **Action**: Prompt for new chat model first, then handle summary model based on new chat model

#### EC2.6: User Cancels Summary Model Re-selection
- **When**: User cancels during summary model selection for loaded session
- **Action**: Disable summarization for session, continue without summary capability

---

## Flow 3: User in Chat Session Creates New Session

### Main Flow
1. **Menu Command**
   - User types `/menu` during chat
   - Display chat menu options

2. **Switch Sessions Selection**
   - User selects "Switch Sessions" option
   - Display existing sessions + "new" option

3. **New Session Selection**
   - User types "new"
   - Begin new session creation process

4. **Model Selection**
   - Display available models table
   - User selects chat model

5. **Preferences Collection**
   - Markdown rendering preference (y/n)
   - Thinking blocks preference (y/n)

6. **System Prompt Selection**
   - Display available system prompts (if any)
   - User selects prompt or chooses "no"

7. **Summary Model Validation & Selection**
   - Same logic as Flow 1, step 6

8. **Session Switch Complete**
   - Stop background services for old session
   - Display session info panel for new session
   - Start background services for new session
   - Ready for user input

### Edge Cases

#### EC3.1: User Cancels Menu Navigation
- **When**: User types 'q' at any menu level
- **Action**: Return to original chat session

#### EC3.2: User Cancels New Session Creation
- **When**: User cancels during model selection or preferences
- **Action**: Return to session selection menu

#### EC3.3: User Cancels Summary Model Selection
- **When**: User cancels during summary model selection
- **Action**: Return to session selection menu (new session not created)

#### EC3.4: Error During Session Switch
- **When**: Error occurs during session creation or switching
- **Action**: Display error, return to original session, keep original session active

---

## Flow 4: User in Chat Session Switches to Another Session

### Main Flow
1. **Menu Command**
   - User types `/menu` during chat
   - Display chat menu options

2. **Switch Sessions Selection**
   - User selects "Switch Sessions" option
   - Display existing sessions table

3. **Existing Session Selection**
   - User selects session number
   - Load target session metadata

4. **Preferences Collection**
   - Markdown rendering preference (y/n)
   - Thinking blocks preference (y/n)

5. **Session Validation & Summary Model Check**
   - Same validation logic as Flow 2, step 4

6. **Summary Model Selection** (if needed)
   - Same logic as Flow 2, step 5

7. **Session Switch Complete**
   - Stop background services for old session
   - Display session info panel for new session
   - Display chat history for switched session
   - Start background services for new session
   - Ready for user input

### Edge Cases

#### EC4.1: User Cancels Session Switch
- **When**: User types 'q' during session selection
- **Action**: Return to original chat session

#### EC4.2: Target Session Invalid/Corrupted
- **When**: Selected session cannot be loaded
- **Action**: Display error, return to session selection, keep original session active

#### EC4.3: User Cancels Summary Model Re-selection
- **When**: User cancels during summary model selection for target session
- **Action**: Return to session selection menu, keep original session active

#### EC4.4: Target Session Models All Invalid
- **When**: Target session has invalid chat and summary models
- **Action**: Prompt to fix models or return to original session

---

## UI Flow Order (All Scenarios)

The UI elements must appear in this exact order for consistency:

1. **Welcome/Context Message**
2. **Session/Model Selection**
3. **Preferences Collection** (Markdown, Thinking)
4. **System Prompt Selection**
5. **Summary Model Selection** (if needed)
6. **Session Info Panel Display**
7. **Chat History Display** (if applicable)
8. **Ready for User Input**

## Error Handling Principles

1. **Non-Destructive**: Never delete or corrupt existing sessions
2. **Graceful Fallback**: Provide options to continue without summary capability
3. **Clear Communication**: Always explain why summary model selection is needed
4. **User Choice**: Allow users to cancel operations and return to safe state
5. **Recovery**: Provide clear paths to fix invalid states

## Summary Model Selection Messages

### Info Messages
- **New unsupported model**: "The selected model '{model}' doesn't support structured summarization. Please select a compatible model to use for generating conversation summaries."
- **Invalid stored model**: "The stored summary model '{model}' is no longer supported for summaries. Please select a new compatible model."
- **Unavailable stored model**: "The stored summary model '{model}' is no longer available. Please select a new model."

### Success Messages
- **Selection complete**: "Summary model set to '{model}' for this session"
- **Using chat model**: "Using chat model '{model}' for summaries"

### Error Messages
- **No compatible models**: "No models available for summarization. Please install compatible models."
- **Selection failed**: "Summary model selection failed. Summarization will be disabled for this session."

## Testing Requirements

Each flow must be tested with:
1. Supported chat models
2. Unsupported chat models
3. Sessions with valid stored summary models
4. Sessions with invalid stored summary models
5. Sessions with missing stored summary models
6. User cancellation at each step
7. Network/API error conditions
8. File system error conditions
9. Concurrent session access scenarios

## Implementation Notes

- All summary model validation must happen before session info display
- Background services should only start after complete session setup
- Session metadata updates must be atomic (save completely or not at all)
- UI state must be recoverable if operations fail partway through
- Logging should capture all decision points for debugging
