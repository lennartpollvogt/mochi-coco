"""
Chat interface styling module using Rich for enhanced visual presentation.
"""

from rich.console import Console
from rich.panel import Panel
from rich.box import ROUNDED
from rich.style import Style
from rich.text import Text
from typing import Optional


class ChatInterface:
    """Handles the visual presentation of chat interface elements using Rich."""

    def __init__(self):
        """Initialize the chat interface with Rich console."""
        self.console = Console()

        # Define styles for consistency
        self.user_style = Style(color="bright_cyan", bold=True)
        self.assistant_style = Style(color="bright_magenta", bold=True)

        # Panel box styles
        self.box_style = ROUNDED

    def print_user_header(self) -> None:
        """Print a styled header for user messages."""
        user_text = Text("🧑 You", style=self.user_style)
        panel = Panel(
            user_text,
            style="bright_cyan",
            box=self.box_style,
            padding=(0, 1),
            expand=False
        )
        self.console.print(panel)

    def print_assistant_header(self) -> None:
        """Print a styled header for assistant messages."""
        assistant_text = Text("🤖 Assistant", style=self.assistant_style)
        panel = Panel(
            assistant_text,
            style="bright_magenta",
            box=self.box_style,
            padding=(0, 1),
            expand=False
        )
        self.console.print(panel)

    def print_system_message(self, message: str, style: str = "yellow") -> None:
        """
        Print a system message with styled panel.

        Args:
            message: The system message to display
            style: Rich style for the message (default: "yellow")
        """
        panel = Panel(
            message,
            style=style,
            box=self.box_style,
            padding=(0, 1),
            title="System",
            title_align="left"
        )
        self.console.print(panel)

    def print_info_message(self, message: str, title: Optional[str] = None) -> None:
        """
        Print an informational message with styled panel.

        Args:
            message: The information message to display
            title: Optional title for the panel
        """
        panel = Panel(
            message,
            style="cyan",
            box=self.box_style,
            padding=(0, 1),
            title=title or "Info",
            title_align="left"
        )
        self.console.print(panel)

    def print_error_message(self, message: str) -> None:
        """
        Print an error message with styled panel.

        Args:
            message: The error message to display
        """
        panel = Panel(
            message,
            style="red",
            box=self.box_style,
            padding=(0, 1),
            title="Error",
            title_align="left"
        )
        self.console.print(panel)

    def print_success_message(self, message: str) -> None:
        """
        Print a success message with styled panel.

        Args:
            message: The success message to display
        """
        panel = Panel(
            message,
            style="green",
            box=self.box_style,
            padding=(0, 1),
            title="Success",
            title_align="left"
        )
        self.console.print(panel)

    def print_separator(self) -> None:
        """Print a visual separator between messages."""
        self.console.print()

    def print_session_info(self, session_id: str, model: str, markdown: bool, thinking: bool) -> None:
        """
        Print session information with integrated commands in a styled panel.

        Args:
            session_id: The session ID
            model: The model being used
            markdown: Whether markdown is enabled
            thinking: Whether thinking blocks are enabled
        """
        # Session info
        info_text = Text()
        info_text.append(f"Session ID: {session_id}\n", style="white")
        info_text.append(f"Model: {model}\n", style="magenta")
        info_text.append(f"Markdown: {'Enabled' if markdown else 'Disabled'}\n", style="cyan")
        info_text.append(f"Thinking Blocks: {'Enabled' if thinking else 'Disabled'}\n", style="cyan")

        # Add commands section
        info_text.append("\n💡 Available Commands:\n", style="bold bright_green")
        info_text.append("• /menu - Open the main menu\n", style="white")
        info_text.append("• /edit - Edit a previous message\n", style="white")
        info_text.append("• /exit or /quit - Exit the application", style="white")

        panel = Panel(
            info_text,
            style="bright_blue",
            box=self.box_style,
            padding=(0, 1),
            title="💬 Chat Session",
            title_align="left"
        )
        self.console.print(panel)
