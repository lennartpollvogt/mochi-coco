"""
Session manager for handling chat session lifecycle and operations.
"""

from typing import Optional, Tuple, TYPE_CHECKING
import typer

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui import ModelSelector

from .system_prompt_service import SystemPromptService
from ..ui.system_prompt_menu_handler import SystemPromptMenuHandler, SystemPromptSelectionContext



class SessionManager:
    """Manages chat session lifecycle, creation, and configuration."""

    def __init__(self, model_selector: "ModelSelector"):
        self.model_selector = model_selector
        # Import here to avoid circular imports
        from ..ui import ChatInterface
        self.chat_interface = ChatInterface()

        # Initialize system prompt services
        self.system_prompt_service = SystemPromptService()
        self.system_prompt_menu_handler = SystemPromptMenuHandler(
            self.system_prompt_service
        )

    def initialize_session(self) -> Tuple[Optional["ChatSession"], Optional[str], bool, bool, Optional[str]]:
        """
        Initialize a chat session - either select existing or create new.

        Returns:
            Tuple of (session, selected_model, markdown_enabled, show_thinking, system_prompt_content)
        """
        session, selected_model, markdown_enabled, show_thinking = self.model_selector.select_session_or_new()

        if session is None and selected_model is None:
            return None, None, False, False, None

        # Handle system prompt selection for new sessions
        system_prompt_content = None
        if session is None:  # New session
            if self.system_prompt_service.has_system_prompts():
                system_prompt_content = self.system_prompt_menu_handler.select_system_prompt(
                    SystemPromptSelectionContext.NEW_SESSION
                )

        return session, selected_model, markdown_enabled, show_thinking, system_prompt_content

    def setup_session(self, session: Optional["ChatSession"], selected_model: Optional[str],
                     system_prompt_content: Optional[str] = None) -> Tuple[Optional["ChatSession"], Optional[str]]:
        """
        Set up the session for chatting - create new if needed or load existing.

        Args:
            session: Existing session or None for new session
            selected_model: Selected model name
            system_prompt_content: System prompt content for new sessions

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

            # Add system prompt if provided
            if system_prompt_content:
                session.add_system_message(system_prompt_content)

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
