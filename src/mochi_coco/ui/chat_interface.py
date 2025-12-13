"""
Chat interface styling module using Rich for enhanced visual presentation.
"""

# Import with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING, Optional

from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

if TYPE_CHECKING:
    from ..services import ContextWindowInfo
    from ..tools.config import ToolSettings


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
            expand=False,
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
            expand=False,
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
            title_align="left",
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
            title_align="left",
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
            title_align="left",
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
            title_align="left",
        )
        self.console.print(panel)

    def print_separator(self) -> None:
        """Print a visual separator between messages."""
        self.console.print()

    def print_session_info(
        self,
        session_id: str,
        model: str,
        markdown: bool,
        thinking: bool,
        summary_model: Optional[str] = None,
        tool_settings: Optional["ToolSettings"] = None,
        session_summary: Optional[dict] = None,
        context_info: Optional["ContextWindowInfo"] = None,
    ) -> None:
        """
        Print session information with integrated commands in a styled panel.

        Args:
            session_id: The session ID
            model: The model being used
            markdown: Whether markdown is enabled
            thinking: Whether thinking blocks are enabled
            summary_model: The summary model being used (if configured)
            tool_settings: The tool settings for this session (if configured)
            session_summary: The session summary dictionary (if available)
            context_info: The context window usage information (if available)
        """
        # Session info
        info_text = Text()
        info_text.append(f"Session ID: {session_id}\n", style="white")
        info_text.append(f"Model: {model}\n", style="magenta")

        # Summary model info
        if summary_model:
            info_text.append(f"Summary Model: {summary_model}\n", style="magenta")
        else:
            info_text.append("Summary Model: Not configured\n", style="dim")

        # Context window info
        if context_info and context_info.has_valid_data:
            percentage = f"({context_info.percentage:.1f}%)"
            info_text.append(
                f"Context Window: {context_info.current_usage:,} / {context_info.max_context:,} {percentage}\n",
                style="cyan",
            )
        elif context_info and context_info.error_message:
            info_text.append(
                f"Context Window: {context_info.error_message}\n", style="dim"
            )
        else:
            info_text.append("Context Window: Not available\n", style="dim")

        # Tools info
        if tool_settings and tool_settings.is_enabled():
            if tool_settings.tool_group:
                info_text.append(
                    f"Tool Group: {tool_settings.tool_group}\n", style="yellow"
                )
            elif tool_settings.tools:
                tools_str = ", ".join(tool_settings.tools)
                info_text.append(f"Tools: {tools_str}\n", style="yellow")

            # Tool execution policy
            policy_display = {
                "always_confirm": "Always confirm",
                "never_confirm": "Never confirm",
                "confirm_destructive": "Confirm destructive",
            }
            policy_text = policy_display.get(
                tool_settings.execution_policy.value,
                tool_settings.execution_policy.value,
            )
            info_text.append(f"Tool Policy: {policy_text}\n", style="yellow")
        else:
            info_text.append("Tools: None\n", style="dim")
            info_text.append("Tool Policy: Not applicable\n", style="dim")

        info_text.append(
            f"Markdown: {'Enabled' if markdown else 'Disabled'}\n", style="cyan"
        )
        info_text.append(
            f"Thinking Blocks: {'Enabled' if thinking else 'Disabled'}\n", style="cyan"
        )

        # Session summary
        if session_summary and isinstance(session_summary, dict):
            summary_text = session_summary.get("summary", "")
            topics = session_summary.get("topics", [])

            if summary_text:
                info_text.append("Summary: ", style="bold green")
                info_text.append(f"{summary_text}\n", style="green")

                # Display topics if available
                if topics:
                    info_text.append("Topics:\n", style="bold green")
                    for topic in topics:
                        info_text.append(f"  • {topic}\n", style="green")
            else:
                info_text.append("Summary: Not available\n", style="dim")
        else:
            info_text.append("Summary: Not available\n", style="dim")

        # Add commands section
        info_text.append("\n💡 Available Commands:\n", style="bold bright_green")
        info_text.append("• /menu - Open the main menu\n", style="white")
        info_text.append("• /status - Show session information\n", style="white")
        info_text.append("• /edit - Edit a previous message\n", style="white")
        info_text.append("• /exit or /quit - Exit the application", style="white")

        panel = Panel(
            info_text,
            style="bright_blue",
            box=self.box_style,
            padding=(0, 1),
            title="💬 Chat Session",
            title_align="left",
        )
        self.console.print(panel)
