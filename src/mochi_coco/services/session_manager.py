"""
Session manager for handling chat session lifecycle and operations.
"""

from typing import Optional, Tuple, TYPE_CHECKING
import typer

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui import ModelSelector



class SessionManager:
    """Manages chat session lifecycle, creation, and configuration."""

    def __init__(self, model_selector: "ModelSelector"):
        self.model_selector = model_selector
        # Import here to avoid circular imports
        from ..ui import ChatInterface
        self.chat_interface = ChatInterface()

    def initialize_session(self) -> Tuple[Optional["ChatSession"], Optional[str], bool, bool]:
        """
        Initialize a chat session - either select existing or create new.

        Returns:
            Tuple of (session, selected_model, markdown_enabled, show_thinking)
        """
        session, selected_model, markdown_enabled, show_thinking = self.model_selector.select_session_or_new()

        if session is None and selected_model is None:
            return None, None, False, False

        return session, selected_model, markdown_enabled, show_thinking

    def setup_session(self, session: Optional["ChatSession"], selected_model: Optional[str]) -> Tuple[Optional["ChatSession"], Optional[str]]:
        """
        Set up the session for chatting - create new if needed or load existing.

        Args:
            session: Existing session or None for new session
            selected_model: Selected model name

        Returns:
            Tuple of (final_session, final_model)
        """
        if session is None and selected_model is None:
            typer.secho("Exiting.", fg=typer.colors.YELLOW)
            return None, None

        # Handle new session
        if session is None:
            if not selected_model:
                typer.secho("No model selected. Exiting.", fg=typer.colors.YELLOW)
                return None, None

            from ..chat import ChatSession
            session = ChatSession(model=selected_model)
            # Removed redundant messages - info is shown in chat session panel
            return session, selected_model
        else:
            # Handle existing session
            selected_model = session.metadata.model
            # Chat history will be displayed after session info panel in chat controller
            return session, selected_model

    def display_session_info(self, markdown_enabled: bool, show_thinking: bool) -> None:
        """Display session information and available commands."""
        # This method is now handled by ChatInterface in the chat controller
        # Keeping for backward compatibility but functionality moved to ChatController
        pass
