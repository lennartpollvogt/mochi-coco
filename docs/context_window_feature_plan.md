# Context Window Usage Feature Implementation Plan

## Overview

This document outlines the implementation plan for adding context window usage information to the Chat Session panel in Mochi Coco. The feature will display current context usage alongside the maximum context window for the selected LLM model (e.g., "Context Window: 961/262144 (0.4%)").

The implementation follows a **simplified on-demand approach** where context information is calculated only when needed: during session startup or when the user types the `/status` command.

## Background

Currently, the Chat Session panel displays various session information but lacks context window usage data. Users can see the maximum context window during model selection but have no visibility into current usage during conversations. This information is crucial for understanding when conversations might hit context limits and how much conversational history is being processed.

## Requirements

### Functional Requirements
- Display current context usage vs maximum context window in the Chat Session panel
- Calculate usage **on-demand only** when session starts/resumes or user types `/status`
- Use the **currently selected model** for both max context and usage calculations
- Calculate usage from chat history by analyzing `eval_count` and `prompt_eval_count` from assistant messages
- Handle edge cases where context data might be missing or incomplete
- Show information in both session startup display and `/status` command
- Format: "Context Window: {current}/{max} ({percentage}%)"

### Technical Requirements
- Follow existing codebase architecture patterns
- Maintain backward compatibility with existing sessions
- Handle tool calls correctly (exclude when `tool_calls` is not null)
- Use only the most recent valid assistant message for context calculation
- Gracefully handle missing or invalid data
- No background processing or caching - calculate fresh each time
- Always use fresh model information to handle model updates

## Architecture Overview

### Current System Analysis

**Relevant Components:**
- `ModelInfo` class: Contains `context_length` field for maximum context window
- `SessionMessage` class: Contains `eval_count` and `prompt_eval_count` fields
- `ChatInterface.print_session_info()`: Displays session information panel
- `ChatUIOrchestrator`: Orchestrates UI display operations
- `CommandProcessor`: Handles `/status` command

**Simplified Data Flow:**
```
Session Start/Resume OR /status Command → Context Calculation Trigger
Current Model + Current Session History → Fresh Context Usage Calculation
Fresh Model Information → Max Context Length → UI Display
```

**Key Simplification**: Context is calculated only when needed, using the current model and complete session history. No caching, no model versioning, no background processing.

## Implementation Plan

### Phase 1: Context Window Service

**File:** `src/mochi_coco/services/context_window_service.py` (new)

Create a dedicated service to handle on-demand context window calculations:

```python
@dataclass
class ContextWindowInfo:
    current_usage: int
    max_context: int
    percentage: float
    has_valid_data: bool
    error_message: Optional[str] = None

class ContextWindowService:
    def __init__(self, ollama_client: OllamaClient):
        self.client = ollama_client
    
    def calculate_context_usage_on_demand(self, session: ChatSession, current_model: str) -> ContextWindowInfo:
        """
        Calculate context usage on-demand for the current model and session state.
        
        Only called when:
        1. Session is started/resumed 
        2. User types /status command
        
        Args:
            session: Current chat session with message history
            current_model: Currently selected model
        """
        # Get fresh model info from server (no caching)
        max_context = self._get_current_model_context_length(current_model)
        if not max_context:
            return self._create_error_info("Model context length unavailable")
        
        # Calculate current usage from session history
        current_usage = self._calculate_current_usage_from_history(session.messages)
        if current_usage is None:
            return self._create_error_info("No valid context data in session", max_context)
        
        percentage = (current_usage / max_context) * 100
        
        return ContextWindowInfo(
            current_usage=current_usage,
            max_context=max_context,
            percentage=percentage,
            has_valid_data=True
        )
    
    def _get_current_model_context_length(self, model_name: str) -> Optional[int]:
        """Retrieve maximum context window from current model information."""
        # Always fetch fresh model info - no caching needed for on-demand approach
        
    def _calculate_current_usage_from_history(self, messages: List[SessionMessage]) -> Optional[int]:
        """Calculate usage from the most recent valid assistant message."""
        # Find last assistant message with tool_calls as null
        # Sum eval_count + prompt_eval_count
        # Validate data integrity before calculation
    
    def _create_error_info(self, error_message: str, max_context: int = 0) -> ContextWindowInfo:
        """Create error ContextWindowInfo object."""
```

**Key Methods:**

1. **`calculate_context_usage_on_demand()`**
   - Primary interface triggered only on session start or `/status` command
   - Uses current model only (ignores historical model changes)
   - Gets fresh model info each time
   - Returns structured data with comprehensive error handling

2. **`_get_current_model_context_length()`**
   - Retrieves maximum context window from fresh model information
   - No caching - always gets current model capabilities
   - Handles cases where model is no longer available

3. **`_calculate_current_usage_from_history()`**
   - Finds most recent assistant message with `tool_calls` as null
   - Sums `eval_count + prompt_eval_count`
   - Validates data integrity before calculation
   - Simple approach: represents how much context current model would use

### Phase 2: Service Integration

**Files to Modify:**
- `src/mochi_coco/services/__init__.py`
- `src/mochi_coco/chat_controller.py`

**Changes:**

1. **Service Registration:**
   ```python
   # In services/__init__.py
   from .context_window_service import ContextWindowService, ContextWindowInfo
   
   # In chat_controller.py
   self.context_window_service = ContextWindowService(self.client)
   ```

2. **Dependency Injection:**
   - Pass service to UI orchestrator when needed
   - Service only used at specific trigger points

### Phase 3: UI Layer Updates

**File:** `src/mochi_coco/ui/chat_interface.py`

**Modifications to `print_session_info()` method:**

```python
def print_session_info(
    self,
    session_id: str,
    model: str,
    markdown: bool,
    thinking: bool,
    summary_model: Optional[str] = None,
    tool_settings: Optional["ToolSettings"] = None,
    session_summary: Optional[dict] = None,
    context_info: Optional["ContextWindowInfo"] = None,  # NEW PARAMETER
) -> None:
```

**Display Logic:**
```python
# Add after model information
if context_info and context_info.has_valid_data:
    percentage = f"({context_info.percentage:.1f}%)"
    info_text.append(
        f"Context Window: {context_info.current_usage:,} / {context_info.max_context:,} {percentage}\n", 
        style="cyan"
    )
elif context_info and context_info.error_message:
    info_text.append(f"Context Window: {context_info.error_message}\n", style="dim")
else:
    info_text.append("Context Window: Not available\n", style="dim")
```

### Phase 4: Orchestrator Updates

**File:** `src/mochi_coco/ui/chat_ui_orchestrator.py`

**Modify `display_session_setup()` method:**

```python
def display_session_setup(
    self,
    session: "ChatSession",
    model: str,
    markdown_enabled: bool,
    show_thinking: bool,
    context_window_service: Optional["ContextWindowService"] = None,  # NEW PARAMETER
) -> None:
    """Display session info with on-demand context calculation."""
    
    # Calculate context window info ON-DEMAND only at session start
    context_info = None
    if context_window_service:
        try:
            context_info = context_window_service.calculate_context_usage_on_demand(
                session, model  # Use current model, not historical models
            )
        except Exception as e:
            context_info = ContextWindowInfo(
                current_usage=0, max_context=0, percentage=0.0,
                has_valid_data=False, error_message=f"Calculation failed: {str(e)}"
            )
    
    # Extract additional session metadata
    summary_model = session.metadata.summary_model
    tool_settings = session.get_tool_settings()
    session_summary = session.metadata.summary if session.metadata else None

    self.chat_interface.print_session_info(
        session_id=session.session_id,
        model=model,
        markdown=markdown_enabled,
        thinking=show_thinking,
        summary_model=summary_model,
        tool_settings=tool_settings,
        session_summary=session_summary,
        context_info=context_info,  # NEW PARAMETER
    )
```

### Phase 5: Command Integration

**File:** `src/mochi_coco/commands/command_processor.py`

**Update `/status` command to include context window info:**

```python
def _handle_status_command(self, session: ChatSession) -> CommandResult:
    """Handle /status command with on-demand context calculation."""
    
    # Get current model (not historical models from session)
    current_model = session.model
    
    # Calculate context info ON-DEMAND only when /status is typed
    context_info = None
    if hasattr(self, 'context_window_service') and self.context_window_service:
        try:
            context_info = self.context_window_service.calculate_context_usage_on_demand(
                session, current_model
            )
        except Exception as e:
            context_info = ContextWindowInfo(
                current_usage=0, max_context=0, percentage=0.0,
                has_valid_data=False, error_message="Unable to calculate"
            )
    
    # Use existing display logic with new context_info parameter
    chat_interface.print_session_info(
        # ... existing parameters ...
        context_info=context_info,
    )
```

## Error Handling Strategy

### Graceful Degradation
- Display "Not available" when context data is missing
- Show specific error messages for calculation failures
- Never crash the application due to context calculation issues
- Always allow the session to continue normally

### Edge Cases
1. **No assistant messages**: Display "No usage data"
2. **Missing eval_count/prompt_eval_count**: Display "Incomplete data"
3. **Model not found**: Display "Model info unavailable"
4. **All messages have tool_calls**: Find first message without tool_calls
5. **Network/API errors**: Display "Unable to calculate"
6. **Model context length unavailable**: Display "Model context length unavailable"

### Validation Rules
- Ensure `eval_count` and `prompt_eval_count` are positive integers
- Validate that calculated usage doesn't exceed reasonable limits
- Handle network timeouts gracefully with fallback messaging
- Always fetch fresh model information to handle model updates

### Simplified Error Scenarios
Since we only deal with the current model and calculate on-demand:
- No complex mixed-model error handling needed
- No cache invalidation or versioning issues
- No background processing errors
- Simple, predictable error conditions

## Testing Strategy

### Unit Tests
**File:** `tests/unit/test_context_window_service.py`

Test scenarios:
- Valid context calculation with complete data
- Missing eval_count/prompt_eval_count handling
- Tool calls filtering logic
- Model context length retrieval
- Network timeout scenarios
- Invalid/corrupted session data
- Model not available scenarios

### Integration Tests
**Files:** 
- `tests/integration/test_context_window_display.py`
- Update existing UI tests

Test scenarios:
- End-to-end context display in session panel
- `/status` command with context info
- Session loading with on-demand context calculation
- Error display in UI components
- Model switching scenarios

### Test Data
Create sample chat history files with:
- Complete context data
- Missing context fields
- Mixed tool calls and regular messages
- Various model conversations

### Simplified Test Scenarios
Focus on two trigger points only:
1. **Session start/resume testing**
2. **`/status` command testing**

No need for complex caching, background processing, or mixed-model tests.

## Performance Considerations

### On-Demand Benefits
1. **Zero startup overhead**: No context calculations during app initialization
2. **No background processing**: Calculations only when explicitly needed
3. **No memory overhead**: No cached data to manage
4. **Fresh data guarantee**: Always current model information
5. **Simple resource usage**: Predictable, user-triggered calculations only

### Performance Characteristics
- Context calculation triggered only at 2 specific points
- Single API call to get model information when needed
- Minimal processing of session message history
- No ongoing resource consumption
- Immediate response for users (calculation happens when info is displayed)

### Calculation Triggers
```
Trigger 1: Session Start/Resume
User starts/resumes chat → display_session_setup() → calculate_context_usage_on_demand()

Trigger 2: Status Command
User types "/status" → _handle_status_command() → calculate_context_usage_on_demand()
```

## Backward Compatibility

### Session Format
- No changes to existing session JSON format
- Feature works with existing chat history files
- Graceful handling of legacy sessions without context data

### API Compatibility
- All existing method signatures remain unchanged (except for new optional parameters)
- New parameters have default values to maintain compatibility
- Existing functionality unaffected if context service is not available

### Simplified Compatibility
Since we only calculate on-demand with current model:
- No version migration needed for old sessions
- No model history tracking required
- Simple fallback for incomplete data

## Model Change Handling

### Simplified Approach
When users change models mid-conversation:
- Context window info reflects the **new current model**
- Calculation uses **existing session history** with **new model's context limits**
- Represents: "How much context would the new model use for this conversation?"
- No complex model transition logic needed

### User Experience
- Context info always relevant to current model selection
- Clear understanding of current model's context usage
- No confusion from historical model context mixing

## Risk Assessment

### Technical Risks
- **Network latency**: Fresh model info requests might be slow
- **Model availability**: Current model might become unavailable
- **Data integrity**: Session data might have invalid context values

### Mitigation Strategies
- Implement timeout handling for model info requests
- Provide clear error messages for all failure scenarios
- Validate all data before processing
- Always allow session to continue even if context calculation fails

### Low Risk Profile
The on-demand approach significantly reduces risks:
- No cache invalidation issues
- No background processing failures
- No complex data synchronization
- Simple, predictable execution paths

## Future Enhancements

### Potential Extensions
1. **Context Usage Warnings**: Alert users when approaching context limits (e.g., >90%)
2. **Context Optimization Tips**: Suggest message history cleanup when context is high
3. **Model Recommendations**: Suggest models with larger context windows when needed
4. **Context History Tracking**: Optional logging of context usage over time
5. **Integration with Summarization**: Automatically suggest summarization at high context usage

### Configuration Options
- Enable/disable context window display via user preferences
- Set warning thresholds for context usage alerts
- Configure timeout values for model information requests

### Expandability
The simple service architecture allows easy extension:
- Additional calculation methods
- Enhanced error reporting
- Integration with other features
- User preference customization

## Conclusion

This implementation plan provides a streamlined approach to adding context window usage information to Mochi Coco. The **on-demand calculation strategy** significantly simplifies the implementation while providing users with accurate, current information about their context usage.

**Key Benefits:**
- **Simple**: No caching, versioning, or background processing complexity
- **Accurate**: Always uses current model and fresh data
- **Performant**: Zero overhead except when explicitly needed
- **Reliable**: Predictable execution with comprehensive error handling
- **User-focused**: Information reflects current model and conversation state

The design follows existing architectural patterns, ensures backward compatibility, and provides a solid foundation for future enhancements. The feature will significantly improve user experience by providing visibility into context usage at the moments when users need this information most.