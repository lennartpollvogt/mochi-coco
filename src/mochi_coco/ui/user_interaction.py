"""
User interaction utilities for handling prompts, input validation, and preference collection.
"""

from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from ..user_prompt import get_user_input_single_line


class UserInteraction:
    """Handles all user prompts, input validation, and preference collection using Rich styling."""

    def __init__(self):
        self.console = Console()

        # Define consistent color scheme
        self.colors = {
            'primary': 'bright_magenta',
            'secondary': 'bright_cyan',
            'success': 'bright_green',
            'warning': 'bright_yellow',
            'error': 'bright_red',
            'info': 'bright_blue'
        }

    def prompt_markdown_preference(self) -> bool:
        """Prompt user for markdown rendering preference."""
        preference_text = Text()
        preference_text.append("📝 Enable markdown formatting for responses?\n", style="bold bright_cyan")
        preference_text.append("This will format code blocks, headers, tables, etc.", style="white")

        preference_panel = Panel(
            preference_text,
            title="Markdown Rendering",
            style=self.colors['info'],
            box=ROUNDED
        )
        self.console.print(preference_panel)

        try:
            choice = get_user_input_single_line("Enable markdown? (Y/n): ")
            if not choice:  # Default to Y if empty
                choice = "Y"
        except (EOFError, KeyboardInterrupt):
            self._display_cancelled()
            return True  # Default to enabled
        return choice.lower() in {"y", "yes", ""}

    def prompt_thinking_display(self) -> bool:
        """Prompt user for thinking block display preference."""
        thinking_text = Text()
        thinking_text.append("🤔 Show model's thinking process in responses?\n", style="bold bright_cyan")
        thinking_text.append("This will display thinking blocks as formatted quotes.", style="white")

        thinking_panel = Panel(
            thinking_text,
            title="Thinking Block Display",
            style=self.colors['info'],
            box=ROUNDED
        )
        self.console.print(thinking_panel)

        try:
            choice = get_user_input_single_line("Show thinking blocks? (y/N): ")
            if not choice:  # Default to N if empty
                choice = "N"
        except (EOFError, KeyboardInterrupt):
            self._display_cancelled()
            return False  # Default to disabled
        return choice.lower() in {"y", "yes"}

    def get_user_choice(self, prompt: str, valid_options: Optional[List[str]] = None) -> str:
        """
        Get user input with optional validation against valid options.

        Args:
            prompt: The prompt to display to the user
            valid_options: Optional list of valid options to validate against

        Returns:
            The user's input as a string
        """
        while True:
            try:
                choice = get_user_input_single_line(f"{prompt} ")

                if valid_options is None:
                    return choice

                if choice.lower() in [opt.lower() for opt in valid_options]:
                    return choice

                self.display_error(f"Please enter one of: {', '.join(valid_options)}")

            except (EOFError, KeyboardInterrupt):
                self._display_cancelled()
                return ""

    def confirm_action(self, message: str, default: bool = False) -> bool:
        """
        Ask user for confirmation of an action.

        Args:
            message: The confirmation message to display
            default: Default value if user just presses enter

        Returns:
            True if user confirms, False otherwise
        """
        default_text = "Y/n" if default else "y/N"
        default_value = "yes" if default else "no"

        try:
            choice = get_user_input_single_line(f"{message} ({default_text}): ")
            if not choice:  # Use default if empty
                choice = default_value
            return choice.lower() in {"y", "yes"}
        except (EOFError, KeyboardInterrupt):
            self._display_cancelled()
            return False

    def get_numeric_choice(self, prompt: str, max_value: int, allow_quit: bool = True) -> Optional[int]:
        """
        Get a numeric choice from the user within a specified range.

        Args:
            prompt: The prompt to display
            max_value: Maximum valid number (1-based)
            allow_quit: Whether to allow 'q' to quit

        Returns:
            The selected number (1-based) or None if quit/cancelled
        """
        quit_text = " or 'q' to quit" if allow_quit else ""
        full_prompt = f"{prompt} (1-{max_value}){quit_text}:"

        while True:
            try:
                choice = get_user_input_single_line(f"{full_prompt} ")

                if allow_quit and choice.lower() in {'q', 'quit', 'exit'}:
                    return None

                try:
                    number = int(choice)
                    if 1 <= number <= max_value:
                        return number
                    else:
                        self.display_error(f"Please enter a number between 1 and {max_value}")
                except ValueError:
                    self.display_error("Please enter a valid number")

            except (EOFError, KeyboardInterrupt):
                self._display_cancelled()
                return None

    @staticmethod
    def get_user_input(prompt: str = "Enter your choice:") -> str:
        """
        Get basic user input with error handling.

        Args:
            prompt: The prompt to display

        Returns:
            The user's input, empty string if cancelled
        """
        try:
            return get_user_input_single_line(f"{prompt} ")
        except (EOFError, KeyboardInterrupt):
            # Keep static method behavior for backward compatibility
            console = Console()
            panel = Panel("👋 Operation cancelled.", style="bright_yellow", box=ROUNDED)
            console.print(panel)
            return ""

    def display_error(self, message: str) -> None:
        """Display an error message to the user."""
        error_panel = Panel(f"❌ {message}", style=self.colors['error'], box=ROUNDED)
        self.console.print(error_panel)

    def display_warning(self, message: str) -> None:
        """Display a warning message to the user."""
        warning_panel = Panel(f"⚠️ {message}", style=self.colors['warning'], box=ROUNDED)
        self.console.print(warning_panel)

    def display_success(self, message: str) -> None:
        """Display a success message to the user."""
        success_panel = Panel(f"✅ {message}", style=self.colors['success'], box=ROUNDED)
        self.console.print(success_panel)

    def display_info(self, message: str) -> None:
        """Display an informational message to the user."""
        info_panel = Panel(f"💡 {message}", style=self.colors['info'], box=ROUNDED)
        self.console.print(info_panel)

    def _display_cancelled(self) -> None:
        """Display a cancellation message."""
        cancel_panel = Panel("👋 Operation cancelled.", style=self.colors['warning'], box=ROUNDED)
        self.console.print(cancel_panel)

    def get_edit_selection(self, max_user_messages: int) -> Optional[int]:
        """
        Get user selection for which message to edit.

        Args:
            max_user_messages: Maximum number of user messages available to edit

        Returns:
            The selected message number (1-based) or None if cancelled
        """
        while True:
            try:
                choice = get_user_input_single_line("")

                if choice.lower() in {'q', 'quit', 'exit'}:
                    return None

                try:
                    number = int(choice)
                    if 1 <= number <= max_user_messages:
                        return number
                    else:
                        self.display_error(f"Please enter a number between 1 and {max_user_messages}")
                        prompt_panel = Panel(f"Select a user message (1-{max_user_messages}) or 'q' to cancel",
                                           style=self.colors['warning'], box=ROUNDED)
                        self.console.print(prompt_panel)
                except ValueError:
                    self.display_error("Please enter a valid number")
                    prompt_panel = Panel(f"Select a user message (1-{max_user_messages}) or 'q' to cancel",
                                       style=self.colors['warning'], box=ROUNDED)
                    self.console.print(prompt_panel)

            except (EOFError, KeyboardInterrupt):
                self._display_cancelled()
                return None
