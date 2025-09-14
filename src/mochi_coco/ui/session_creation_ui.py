"""
UI components specific to session creation flows.

This module provides standardized user interface components for session creation,
selection, and management across all entry points in the application.
"""

from typing import List
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .chat_interface import ChatInterface
from ..services.session_creation_types import SessionCreationContext

# Import with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..chat import ChatSession


class SessionCreationUI:
    """UI components specific to session creation flows."""

    def __init__(self):
        self.console = Console()
        self.chat_interface = ChatInterface()

    def display_welcome(self, context: SessionCreationContext) -> None:
        """Display welcome message appropriate for the context."""
        if context == SessionCreationContext.APPLICATION_STARTUP:
            self._display_startup_welcome()
        elif context == SessionCreationContext.MENU_COMMAND:
            self._display_menu_welcome()
        else:
            self._display_generic_welcome()

    def _display_startup_welcome(self) -> None:
        """Display welcome message for application startup."""
        welcome_test_1 = """🤖 AI Chat with Style"""

        panel = Panel(
            welcome_test_1,
            style="bright_green",
            padding=(1, 2),
            title="🍡 Welcome to Mochi-Coco!",
            title_align="center"
        )
        self.console.print(panel)

    def _display_menu_welcome(self) -> None:
        """Display welcome message for menu-initiated session creation."""
        self.chat_interface.print_info_message(
            "🔄 Session Management",
            "Select or create a chat session"
        )

    def _display_generic_welcome(self) -> None:
        """Display generic welcome message for other contexts."""
        self.chat_interface.print_info_message(
            "💬 Session Selection",
            "Choose your chat session"
        )

    def display_existing_sessions(self, sessions: List["ChatSession"]) -> None:
        """Display table of existing sessions with integrated options."""
        table = Table()
        table.add_column("#", style="cyan", width=3)
        table.add_column("Session ID", style="magenta", width=12)
        table.add_column("Model", style="green", width=20)
        table.add_column("Preview", style="white", width=35)
        table.add_column("Messages", style="blue", width=8, justify="center")

        for i, session in enumerate(sessions, 1):
            preview = self._get_session_preview(session)
            table.add_row(
                str(i),
                session.session_id,
                session.metadata.model,
                preview,
                str(session.metadata.message_count)
            )

        # Create options text
        session_count = len(sessions)
        options_text = Text()
        options_text.append("\n💡 Options:\n", style="bold bright_yellow")
        options_text.append(f"• 📝 Select session (1-{session_count})\n", style="white")
        options_text.append("• 🆕 Type 'new' for new chat\n", style="white")
        options_text.append("• 🗑️ Type '/delete <number>' to delete session\n", style="white")
        options_text.append("• 👋 Type 'q' to quit", style="white")

        # Combine table and options
        combined_content = Group(table, options_text)

        panel = Panel(combined_content, title="💬 Previous Sessions", padding=(1, 1))
        self.console.print(panel)

    def get_session_choice(self, session_count: int) -> str:
        """Get user's session selection choice."""
        choice = input("Enter your choice: ").strip()

        # Handle delete command
        if choice.startswith('/delete '):
            try:
                delete_num = choice.split(' ')[1]
                return f"delete_{delete_num}"
            except (IndexError, ValueError):
                return "invalid"

        return choice.lower()

    def display_deletion_success(self, session_id: str) -> None:
        """Display successful session deletion."""
        self.chat_interface.print_success_message(f"Session {session_id} deleted successfully")

    def display_deletion_error(self, session_id: str) -> None:
        """Display session deletion error."""
        self.chat_interface.print_error_message(f"Failed to delete session {session_id}")

    def display_session_creation_start(self, context: SessionCreationContext) -> None:
        """Display message when starting session creation process."""
        if context == SessionCreationContext.APPLICATION_STARTUP:
            self.chat_interface.print_info_message(
                "🚀 Starting Session",
                "Setting up your chat environment"
            )
        elif context == SessionCreationContext.MENU_COMMAND:
            self.chat_interface.print_info_message(
                "🔄 Session Switch",
                "Loading session management"
            )

    def display_session_creation_success(self, session: "ChatSession", model: str,
                                       context: SessionCreationContext) -> None:
        """Display successful session creation/loading."""
        if context == SessionCreationContext.APPLICATION_STARTUP:
            #self.chat_interface.print_success_message(
            #    f"Session ready! Using {model} (ID: {session.session_id})"
            #)
            pass
        else:
            self.chat_interface.print_success_message(
                f"Switched to session {session.session_id} with {model}"
            )

    def display_no_sessions_available(self) -> None:
        """Display message when no sessions are available."""
        message = """📝 No Previous Sessions Found

This appears to be your first time using Mochi-Coco,
or all previous sessions have been deleted.

Let's create a new chat session!"""

        panel = Panel(
            message,
            title="Welcome!",
            style="yellow",
            padding=(1, 1)
        )
        self.console.print(panel)

    def _get_session_preview(self, session: "ChatSession") -> str:
        """Get a preview of the session content."""
        if not session.messages:
            return "Empty session"

        # Find first user message
        for message in session.messages:
            if message.role == "user":
                content = message.content.strip()
                if len(content) > 50:
                    return content[:47] + "..."
                return content

        return "No user messages"
