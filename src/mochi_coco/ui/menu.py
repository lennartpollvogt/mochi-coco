from typing import List, Optional, Tuple, Union, Literal
import typer
import re
from ..ollama.client import OllamaClient
from ..chat.session import ChatSession
from ..rendering import MarkdownRenderer
from .menu_display import MenuDisplay
from .user_interaction import UserInteraction
from .model_menu_handler import ModelMenuHandler, ModelSelectionContext


class MenuCommandResult:
    """Result of menu command execution."""
    def __init__(self, should_continue: bool = True, refresh_needed: bool = False):
        self.should_continue = should_continue
        self.refresh_needed = refresh_needed


class SessionMenuHandler:
    """Handles session menu commands and operations."""

    def __init__(self):
        self.user_interaction = UserInteraction()

    def parse_command(self, user_input: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Parse menu commands like '/delete 2'.

        Returns:
            Tuple of (command, argument) where argument is session number for applicable commands
        """
        user_input = user_input.strip()

        if not user_input.startswith('/'):
            return None, None

        # Handle /delete <number> command
        delete_match = re.match(r'/delete\s+(\d+)', user_input, re.IGNORECASE)
        if delete_match:
            return 'delete', int(delete_match.group(1))

        return None, None

    def handle_delete_command(self, sessions: List[ChatSession], session_number: int) -> MenuCommandResult:
        """
        Handle deletion of a session.

        Args:
            sessions: List of available sessions
            session_number: 1-based session number to delete

        Returns:
            MenuCommandResult indicating if operation succeeded and if refresh is needed
        """
        if not (1 <= session_number <= len(sessions)):
            self.user_interaction.display_error(f"Invalid session number. Please choose between 1 and {len(sessions)}.")
            return MenuCommandResult(should_continue=True, refresh_needed=False)

        session_to_delete = sessions[session_number - 1]

        # Confirm deletion
        typer.secho(f"\n⚠️  Are you sure you want to delete session {session_to_delete.session_id}?",
                   fg=typer.colors.YELLOW, bold=True)
        # Display preview using Rich
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        preview_panel = Panel(session_to_delete.get_session_summary(), title="Session Preview", style="white")
        console.print(preview_panel)

        confirm = self.user_interaction.confirm_action("Are you sure you want to delete this session?", default=False)

        if confirm:
            if session_to_delete.delete_session():
                self.user_interaction.display_success(f"Session {session_to_delete.session_id} deleted successfully!")
                return MenuCommandResult(should_continue=True, refresh_needed=True)
            else:
                self.user_interaction.display_error(f"Failed to delete session {session_to_delete.session_id}")
        else:
            self.user_interaction.display_info("Deletion cancelled.")

        return MenuCommandResult(should_continue=True, refresh_needed=False)


class ModelSelector:
    def __init__(self, client: OllamaClient, renderer: Optional[MarkdownRenderer] = None):
        self.client = client
        self.renderer = renderer
        self.session_menu_handler = SessionMenuHandler()
        self.menu_display = MenuDisplay(renderer)
        self.model_menu_handler = ModelMenuHandler(client, self.menu_display)
        self.user_interaction = UserInteraction()

    def select_model(self, context: str = ModelSelectionContext.FROM_CHAT) -> Optional[str]:
        """Display model selection menu and return the selected model name."""
        return self.model_menu_handler.select_model(context)

    def select_session_or_new(self) -> tuple[Optional[ChatSession], Optional[str], bool, bool]:
        """
        Allow user to select an existing session or start new.
        Returns (session, model_name, markdown_enabled, show_thinking) tuple.
        """
        self.menu_display.display_welcome_message()

        while True:  # Outer loop to handle session list refresh
            sessions = ChatSession.list_sessions()

            if not sessions:
                return self._handle_no_sessions_scenario()

            result = self._handle_session_selection_menu(sessions)
            if result is not None:
                return result
            # Continue loop if result is None (refresh needed)

    def _handle_no_sessions_scenario(self) -> tuple[Optional[ChatSession], Optional[str], bool, bool]:
        """Handle the case when no sessions exist."""
        self.menu_display.display_no_sessions_message()

        # Keep trying until user selects a model or force-quits
        while True:
            try:
                selected_model = self.model_menu_handler.select_model(
                    context=ModelSelectionContext.NO_SESSIONS
                )

                if selected_model and selected_model != "RETRY":
                    markdown_enabled, show_thinking = self._collect_user_preferences()
                    return None, selected_model, markdown_enabled, show_thinking
                # If selected_model is "RETRY", continue the loop

            except (EOFError, KeyboardInterrupt):
                typer.secho("\nExiting application.", fg=typer.colors.YELLOW)
                return None, None, False, False

    def _handle_session_selection_menu(self, sessions: List[ChatSession]) -> Optional[tuple[Optional[ChatSession], Optional[str], bool, bool]]:
        """
        Handle session selection when sessions exist.
        Returns result tuple or None if refresh is needed.
        """
        self.menu_display.display_sessions_table(sessions)

        while True:  # Loop for user input
            try:
                choice = self.user_interaction.get_user_input("Enter your choice:")

                result = self._process_user_choice(sessions, choice)
                if result == "REFRESH_NEEDED":
                    return None  # Signal refresh needed
                elif result is not None:
                    return result

            except (EOFError, KeyboardInterrupt):
                typer.secho("\nExiting.", fg=typer.colors.YELLOW)
                return None, None, False, False

    def _process_user_choice(self, sessions: List[ChatSession], choice: str) -> Union[tuple[Optional[ChatSession], Optional[str], bool, bool], Literal["REFRESH_NEEDED"], None]:
        """
        Process a single user choice.
        Returns result tuple, None to continue input loop, or "REFRESH_NEEDED" to refresh sessions.
        """
        # Handle quit commands
        if choice.lower() in {'q', 'quit', 'exit'}:
            return None, None, False, False

        # Handle new chat creation
        if choice.lower() == 'new':
            result = self._handle_new_chat_creation()
            if result is None:
                # Model selection was cancelled, returning to session menu
                typer.secho("", fg=typer.colors.WHITE)  # Add blank line for spacing
                return "REFRESH_NEEDED"  # Signal refresh needed to redisplay session list
            return result

        # Handle menu commands (like delete)
        command, argument = self.session_menu_handler.parse_command(choice)
        if command == 'delete' and argument is not None:
            result = self.session_menu_handler.handle_delete_command(sessions, argument)
            if result.refresh_needed:
                return "REFRESH_NEEDED"  # Signal refresh needed
            return None  # Continue input loop

        # Handle session selection by number
        return self._handle_session_number_selection(sessions, choice)

    def _handle_new_chat_creation(self) -> Optional[tuple[Optional[ChatSession], Optional[str], bool, bool]]:
        """Handle creation of a new chat session with proper retry logic."""
        selected_model = self.model_menu_handler.select_model(
            context=ModelSelectionContext.FROM_SESSION_MENU
        )

        if selected_model:
            markdown_enabled, show_thinking = self._collect_user_preferences()
            return None, selected_model, markdown_enabled, show_thinking
        else:
            # Model selection was cancelled - return None to continue session menu loop
            return None

    def _handle_session_number_selection(self, sessions: List[ChatSession], choice: str) -> Optional[tuple[Optional[ChatSession], Optional[str], bool, bool]]:
        """Handle selection of a session by number."""
        try:
            index = int(choice) - 1
            if 0 <= index < len(sessions):
                return self._load_selected_session(sessions[index])
            else:
                self.user_interaction.display_error(f"Please enter a number between 1 and {len(sessions)}, 'new', '/delete <number>', or 'q'")
                return None
        except ValueError:
            self.user_interaction.display_error("Please enter a valid number, 'new', '/delete <number>', or 'q'")
            return None

    def _load_selected_session(self, session: ChatSession) -> tuple[Optional[ChatSession], Optional[str], bool, bool]:
        """Load and validate a selected session."""
        # Check if the session's model is still available
        if not self.model_menu_handler.check_model_availability(session.metadata.model):
            new_model = self.model_menu_handler.handle_unavailable_model(session.metadata.model)
            if new_model:
                session.model = new_model
                session.metadata.model = new_model
                session.save_session()
            else:
                return None, None, False, False

        self.menu_display.display_session_loaded(session.session_id, session.metadata.model)
        markdown_enabled, show_thinking = self._collect_user_preferences()
        return session, session.metadata.model, markdown_enabled, show_thinking

    def _collect_user_preferences(self) -> tuple[bool, bool]:
        """Collect user preferences for markdown and thinking display."""
        markdown_enabled = self.user_interaction.prompt_markdown_preference()
        show_thinking = self.user_interaction.prompt_thinking_display() if markdown_enabled else False
        return markdown_enabled, show_thinking

    def display_chat_history(self, session: ChatSession) -> None:
        """Display the chat history of a session."""
        self.menu_display.display_chat_history(session)
