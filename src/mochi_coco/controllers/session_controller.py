"""
Session controller for handling session-specific operations and message processing.

This module extracts session management logic from ChatController to improve
separation of concerns and provide focused session operations.
"""

from typing import Optional, NamedTuple, List, Mapping, Any, TYPE_CHECKING, Dict
import logging
from ..chat import ChatSession
from ..services import SessionManager
from ..ollama import OllamaClient
from ..rendering.tool_aware_renderer import ToolAwareRenderer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class SessionInitResult(NamedTuple):
    """Result of session initialization."""
    session: Optional[ChatSession]
    model: Optional[str]
    markdown_enabled: bool
    show_thinking: bool
    success: bool


class MessageProcessResult(NamedTuple):
    """Result of message processing."""
    success: bool
    final_chunk: Optional[Any] = None
    error_message: Optional[str] = None


class SessionController:
    """Handles session-specific operations and message processing."""

    def __init__(self, session_manager: SessionManager, client: OllamaClient):
        self.session_manager = session_manager
        self.client = client

    def initialize_session(self) -> SessionInitResult:
        """Initialize a new or existing session."""
        try:
            result = self.session_manager.initialize_session()
            session, model, markdown_enabled, show_thinking, system_prompt = result

            # For new sessions, session will be None initially but model should not be None
            # For existing sessions, both session and model should not be None
            if model is None:
                logger.error("Model is None after initialization")
                return SessionInitResult(None, None, False, False, False)

            # Setup session with system prompt if provided
            session, model = self.session_manager.setup_session(session, model, system_prompt)

            if session is None or model is None:
                logger.error("Session or model is None after setup")
                return SessionInitResult(None, None, False, False, False)

            return SessionInitResult(session, model, markdown_enabled, show_thinking, True)

        except Exception as e:
            logger.error(f"Session initialization failed: {e}", exc_info=True)
            return SessionInitResult(None, None, False, False, False)

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
                text_stream = self.client.chat_stream(model=model, messages=messages, tools=tools)

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
                text_stream = self.client.chat_stream(model=model, messages=messages)
                final_chunk = renderer.render_streaming_response(text_stream)

            if final_chunk:
                # Only add non-tool messages (tool messages are added by renderer)
                # If no tools are enabled, always add the message
                # If tools are enabled, only add if message doesn't have tool_calls
                if not tool_context or not tool_context.get('tools_enabled'):
                    # No tools enabled, always add message
                    session.add_message(chunk=final_chunk)
                elif not (hasattr(final_chunk.message, 'tool_calls') and final_chunk.message.tool_calls):
                    # Tools enabled but this message has no tool calls, add it
                    session.add_message(chunk=final_chunk)
                return MessageProcessResult(True, final_chunk)
            else:
                return MessageProcessResult(False, None, "No response received")

        except Exception as e:
            return MessageProcessResult(False, None, str(e))
