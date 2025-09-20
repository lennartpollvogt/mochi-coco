# Phase 3: Streaming Integration (Continuation)

## 3.1 Tool-Aware Renderer Wrapper
**File**: `src/mochi_coco/rendering/tool_aware_renderer.py`

```python
from typing import Iterator, Dict, Callable, List, Optional, Any, TYPE_CHECKING
from ollama import ChatResponse, Message, Tool
from ..tools.execution_service import ToolExecutionService, ToolExecutionResult
from ..ui.tool_confirmation_ui import ToolConfirmationUI
from ..tools.config import ToolSettings, ToolExecutionPolicy
import logging

if TYPE_CHECKING:
    from ..chat.session import ChatSession
    from ..ollama.client import OllamaClient

logger = logging.getLogger(__name__)

class ToolAwareRenderer:
    """Wrapper that adds tool handling capabilities to existing renderer."""
    
    def __init__(self, base_renderer, tool_execution_service: Optional[ToolExecutionService] = None,
                 confirmation_ui: Optional[ToolConfirmationUI] = None):
        self.base_renderer = base_renderer
        self.tool_execution_service = tool_execution_service
        self.confirmation_ui = confirmation_ui or ToolConfirmationUI()
        self.tool_call_depth = 0  # Track recursive tool calls
        self.max_tool_call_depth = 5  # Prevent infinite recursion
        
    def render_streaming_response(self, text_chunks: Iterator[ChatResponse],
                                 tool_context: Optional[Dict] = None) -> Optional[ChatResponse]:
        """
        Enhanced render method that handles tool calls if context is provided.
        Falls back to base renderer if no tool context.
        """
        if not tool_context or not tool_context.get('tools_enabled'):
            # No tools, use base renderer
            return self.base_renderer.render_streaming_response(text_chunks)
            
        # Extract tool context
        tool_settings = tool_context.get('tool_settings')
        session = tool_context.get('session')
        model = tool_context.get('model')
        client = tool_context.get('client')
        available_tools = tool_context.get('available_tools', [])
        
        if not all([tool_settings, session, model, client]):
            # Missing required context, fall back to base renderer
            logger.warning("Incomplete tool context, falling back to base renderer")
            return self.base_renderer.render_streaming_response(text_chunks)
            
        # Use tool-aware rendering
        return self._render_with_tools(
            text_chunks, tool_settings, session, model, client, available_tools
        )
        
    def _render_with_tools(self, 
                          text_chunks: Iterator[ChatResponse],
                          tool_settings: ToolSettings,
                          session: "ChatSession",
                          model: str,
                          client: "OllamaClient",
                          available_tools: List[Tool]) -> Optional[ChatResponse]:
        """
        Render streaming response with tool call handling.
        """
        accumulated_text = ""
        final_chunk = None
        tool_calls_made = False
        
        # Check recursion depth
        self.tool_call_depth += 1
        if self.tool_call_depth > self.max_tool_call_depth:
            logger.error(f"Max tool call depth ({self.max_tool_call_depth}) exceeded")
            print(f"\n[Error: Maximum tool call depth exceeded]")
            self.tool_call_depth -= 1
            return None
        
        try:
            for chunk in text_chunks:
                # Handle thinking blocks if present (delegate to base renderer logic)
                if hasattr(chunk.message, 'thinking') and chunk.message.thinking:
                    if self.base_renderer.show_thinking:
                        print(chunk.message.thinking, end='', flush=True)
                        
                # Handle regular content
                if chunk.message.content:
                    accumulated_text += chunk.message.content
                    print(chunk.message.content, end='', flush=True)
                    
                # Handle tool calls
                if hasattr(chunk.message, 'tool_calls') and chunk.message.tool_calls:
                    tool_calls_made = True
                    
                    # Process each tool call
                    for tool_call in chunk.message.tool_calls:
                        print(f"\n\n🔧 AI requesting tool: {tool_call.function.name}")
                        
                        tool_result = self._handle_tool_call(
                            tool_call, 
                            tool_settings
                        )
                        
                        if tool_result:
                            # Add tool call message to session
                            self._add_tool_call_to_session(
                                session, chunk.message, tool_call, model
                            )
                            
                            # Add tool response to session
                            self._add_tool_response_to_session(
                                session, tool_call.function.name, tool_result
                            )
                            
                            # Show result to user
                            if self.confirmation_ui:
                                self.confirmation_ui.show_tool_result(
                                    tool_call.function.name,
                                    tool_result.success if isinstance(tool_result, ToolExecutionResult) else True,
                                    tool_result.result if isinstance(tool_result, ToolExecutionResult) else str(tool_result),
                                    tool_result.error_message if isinstance(tool_result, ToolExecutionResult) else None
                                )
                            
                            # Continue conversation with tool result
                            print("\n🤖 Processing tool result...\n")
                            messages = session.get_messages_for_api()
                            
                            # Continue streaming with updated context
                            continuation_stream = client.chat_stream(
                                model, 
                                messages, 
                                tools=available_tools
                            )
                            
                            # Recursively handle continuation (might have more tool calls)
                            continuation_result = self._render_with_tools(
                                continuation_stream,
                                tool_settings,
                                session,
                                model,
                                client,
                                available_tools
                            )
                            
                            # Return the final result from the continuation
                            return continuation_result
                    
                # Check if this is the final chunk
                if chunk.done:
                    chunk.message.content = accumulated_text
                    final_chunk = chunk
                    
            # If we had tool calls but no continuation, something went wrong
            if tool_calls_made and not final_chunk:
                logger.warning("Tool calls made but no final response received")
                    
            return final_chunk
            
        finally:
            self.tool_call_depth -= 1
        
    def _handle_tool_call(self, tool_call: Any, tool_settings: ToolSettings) -> Optional[ToolExecutionResult]:
        """
        Handle a single tool call with confirmation based on policy.
        
        Returns:
            ToolExecutionResult or None if execution was denied
        """
        if not self.tool_execution_service:
            logger.error("Tool execution service not available")
            return ToolExecutionResult(
                success=False,
                result=None,
                error_message="Tool execution service not configured",
                tool_name=tool_call.function.name
            )
            
        tool_name = tool_call.function.name
        arguments = dict(tool_call.function.arguments) if tool_call.function.arguments else {}
        
        # Create confirmation callback
        def confirm_callback(name: str, args: Dict) -> bool:
            if tool_settings.execution_policy == ToolExecutionPolicy.NEVER_CONFIRM:
                return True
            elif tool_settings.execution_policy == ToolExecutionPolicy.ALWAYS_CONFIRM:
                return self.confirmation_ui.confirm_tool_execution(name, args)
            else:
                # CONFIRM_DESTRUCTIVE - future enhancement
                # For now, default to confirming
                return self.confirmation_ui.confirm_tool_execution(name, args)
        
        # Execute the tool
        result = self.tool_execution_service.execute_tool(
            tool_name, 
            arguments,
            tool_settings.execution_policy,
            confirm_callback
        )
        
        return result
        
    def _add_tool_call_to_session(self, session: "ChatSession", message: Message, 
                                  tool_call: Any, model: str):
        """Add tool call message to session."""
        # Create a tool call message that matches the assistant message format
        # but includes tool_calls
        from ..chat.session import SessionMessage
        
        tool_message = SessionMessage(
            role="assistant",
            content=message.content or "",
            model=model
        )
        
        # Add tool_calls as a custom attribute (will be saved in JSON)
        tool_message.tool_calls = [{
            'function': {
                'name': tool_call.function.name,
                'arguments': dict(tool_call.function.arguments) if tool_call.function.arguments else {}
            }
        }]
        
        session.messages.append(tool_message)
        session.metadata.message_count = len(session.messages)
        session.metadata.updated_at = datetime.now().isoformat()
        session.save_session()
        
    def _add_tool_response_to_session(self, session: "ChatSession", 
                                      tool_name: str, result: ToolExecutionResult):
        """Add tool response message to session."""
        from ..chat.session import SessionMessage
        from datetime import datetime
        
        # Create a tool response message
        tool_response = SessionMessage(
            role="tool",
            content=result.result if result.success else f"Error: {result.error_message}",
            model=None  # Tool responses don't have a model
        )
        
        # Add tool_name as a custom attribute
        tool_response.tool_name = tool_name
        
        session.messages.append(tool_response)
        session.metadata.message_count = len(session.messages)
        session.metadata.updated_at = datetime.now().isoformat()
        session.save_session()
```

## 3.2 Update Session Controller
**File**: `src/mochi_coco/controllers/session_controller.py` (modifications)

```python
# Add to imports
from typing import Optional, Dict, Any
from ..tools.config import ToolSettings
from ..rendering.tool_aware_renderer import ToolAwareRenderer
from ..tools.execution_service import ToolExecutionService
from ..tools.schema_service import ToolSchemaService

# Modify process_user_message method
def process_user_message(self, session: ChatSession, model: str,
                         user_input: str, renderer,
                         tool_context: Optional[Dict[str, Any]] = None) -> MessageProcessResult:
    """
    Process a regular user message and get LLM response.
    
    Args:
        session: Current chat session
        model: Model to use
        user_input: User's input message
        renderer: Renderer to use for output
        tool_context: Optional dict with tool-related context
    """
    try:
        # Add user message to session
        session.add_user_message(content=user_input)
        
        # Get messages for API
        messages: List[Mapping[str, Any]] = session.get_messages_for_api()
        
        # Check if tools are enabled
        if tool_context and tool_context.get('tools_enabled'):
            # Stream with tool support
            tools = tool_context.get('tools', [])
            text_stream = self.client.chat_stream(model, messages, tools=tools)
            
            # Create tool-aware renderer if needed
            if not isinstance(renderer, ToolAwareRenderer):
                tool_execution_service = tool_context.get('tool_execution_service')
                renderer = ToolAwareRenderer(renderer, tool_execution_service)
            
            # Add required context for tool handling
            tool_context.update({
                'session': session,
                'model': model,
                'client': self.client,
                'available_tools': tools
            })
            
            final_chunk = renderer.render_streaming_response(text_stream, tool_context)
        else:
            # Regular streaming without tools
            text_stream = self.client.chat_stream(model, messages)
            final_chunk = renderer.render_streaming_response(text_stream)
        
        if final_chunk:
            # Only add non-tool messages (tool messages are added by renderer)
            if not hasattr(final_chunk.message, 'tool_calls') or not final_chunk.message.tool_calls:
                session.add_message(chunk=final_chunk)
            return MessageProcessResult(True, final_chunk)
        else:
            return MessageProcessResult(False, None, "No response received")
            
    except Exception as e:
        return MessageProcessResult(False, None, str(e))
```

## 3.3 Update Chat Session for Better Tool Support
**File**: `src/mochi_coco/chat/session.py` (modifications)

```python
# Add to imports
from typing import Union

# Modify SessionMessage to handle tool-related fields
@dataclass
class SessionMessage:
    role: str
    content: str
    model: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: Optional[str] = None
    eval_count: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    # Add optional tool-related fields
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_name: Optional[str] = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4()).replace("-", "")[:10]
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

# Update get_messages_for_api to handle tool messages properly
def get_messages_for_api(self) -> List[Mapping[str, Any]]:
    """Get messages in format suitable for API calls."""
    messages = []
    for message in self.messages:
        msg_dict = {
            "role": message.role,
            "content": message.content
        }
        
        # Add tool_calls if present
        if hasattr(message, 'tool_calls') and message.tool_calls:
            msg_dict['tool_calls'] = message.tool_calls
            
        # Add tool_name for tool responses
        if hasattr(message, 'tool_name') and message.tool_name:
            msg_dict['tool_name'] = message.tool_name
            
        messages.append(msg_dict)
    
    return messages

# Add method to check if tools are enabled
def has_tools_enabled(self) -> bool:
    """Check if session has tools enabled."""
    if hasattr(self.metadata, 'tools_settings'):
        settings = self.metadata.tools_settings
        if isinstance(settings, dict):
            # Check for tools or tool_group
            return bool(settings.get('tools') or settings.get('tool_group'))
    return False

# Add method to get tool settings
def get_tool_settings(self) -> Optional[ToolSettings]:
    """Get tool settings for this session."""
    if hasattr(self.metadata, 'tools_settings') and self.metadata.tools_settings:
        from ..tools.config import ToolSettings
        return ToolSettings.from_dict(self.metadata.tools_settings)
    return None
```
