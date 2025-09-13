"""
Session controller for handling session-specific operations and message processing.

This module extracts session management logic from ChatController to improve
separation of concerns and provide focused session operations.
"""

from typing import Optional, NamedTuple, List, Mapping, Any, TYPE_CHECKING
import logging
from ..chat import ChatSession
from ..services import SessionManager
from ..ollama import OllamaClient

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
                           user_input: str, renderer) -> MessageProcessResult:
        """Process a regular user message and get LLM response."""
        try:
            # Add user message to session
            session.add_user_message(content=user_input)

            # Get messages for API and stream response
            messages: List[Mapping[str, Any]] = session.get_messages_for_api()
            text_stream = self.client.chat_stream(model, messages)
            final_chunk = renderer.render_streaming_response(text_stream)

            if final_chunk:
                session.add_message(chunk=final_chunk)
                return MessageProcessResult(True, final_chunk)
            else:
                return MessageProcessResult(False, None, "No response received")

        except Exception as e:
            return MessageProcessResult(False, None, str(e))
