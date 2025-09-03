"""
User interaction utilities for handling prompts, input validation, and preference collection.
"""

from typing import List, Optional
import typer


class UserInteraction:
    """Handles all user prompts, input validation, and preference collection."""

    @staticmethod
    def prompt_markdown_preference() -> bool:
        """Prompt user for markdown rendering preference."""
        typer.secho("\n📝 Markdown Rendering", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.secho("Enable markdown formatting for responses?", fg=typer.colors.YELLOW)
        typer.secho("This will format code blocks, headers, tables, etc.", fg=typer.colors.WHITE)

        choice = typer.prompt("Enable markdown? (Y/n)", default="Y", show_default=False)
        return choice.lower() in {"y", "yes", ""}

    @staticmethod
    def prompt_thinking_display() -> bool:
        """Prompt user for thinking block display preference."""
        typer.secho("\n🤔 Thinking Block Display", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.secho("Show model's thinking process in responses?", fg=typer.colors.YELLOW)
        typer.secho("This will display thinking blocks as formatted quotes.", fg=typer.colors.WHITE)

        choice = typer.prompt("Show thinking blocks? (y/N)", default="N", show_default=False)
        return choice.lower() in {"y", "yes"}

    @staticmethod
    def get_user_choice(prompt: str, valid_options: Optional[List[str]] = None) -> str:
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
                choice = input(f"{prompt} ").strip()

                if valid_options is None:
                    return choice

                if choice.lower() in [opt.lower() for opt in valid_options]:
                    return choice

                typer.secho(f"Please enter one of: {', '.join(valid_options)}", fg=typer.colors.RED)

            except (EOFError, KeyboardInterrupt):
                typer.secho("\nOperation cancelled.", fg=typer.colors.YELLOW)
                return ""

    @staticmethod
    def confirm_action(message: str, default: bool = False) -> bool:
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
            choice = typer.prompt(f"{message} ({default_text})", default=default_value, show_default=False)
            return choice.lower() in {"y", "yes"}
        except (EOFError, KeyboardInterrupt):
            typer.secho("\nOperation cancelled.", fg=typer.colors.YELLOW)
            return False

    @staticmethod
    def get_numeric_choice(prompt: str, max_value: int, allow_quit: bool = True) -> Optional[int]:
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
                choice = input(f"{full_prompt} ").strip()

                if allow_quit and choice.lower() in {'q', 'quit', 'exit'}:
                    return None

                try:
                    number = int(choice)
                    if 1 <= number <= max_value:
                        return number
                    else:
                        typer.secho(f"Please enter a number between 1 and {max_value}", fg=typer.colors.RED)
                except ValueError:
                    typer.secho("Please enter a valid number", fg=typer.colors.RED)

            except (EOFError, KeyboardInterrupt):
                typer.secho("\nOperation cancelled.", fg=typer.colors.YELLOW)
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
            return input(f"{prompt} ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.secho("\nOperation cancelled.", fg=typer.colors.YELLOW)
            return ""

    @staticmethod
    def display_error(message: str) -> None:
        """Display an error message to the user."""
        typer.secho(message, fg=typer.colors.RED)

    @staticmethod
    def display_warning(message: str) -> None:
        """Display a warning message to the user."""
        typer.secho(message, fg=typer.colors.YELLOW)

    @staticmethod
    def display_success(message: str) -> None:
        """Display a success message to the user."""
        typer.secho(message, fg=typer.colors.GREEN, bold=True)

    @staticmethod
    def display_info(message: str) -> None:
        """Display an informational message to the user."""
        typer.secho(message, fg=typer.colors.CYAN)

    @staticmethod
    def get_edit_selection(max_user_messages: int) -> Optional[int]:
        """
        Get user selection for which message to edit.

        Args:
            max_user_messages: Maximum number of user messages available to edit

        Returns:
            The selected message number (1-based) or None if cancelled
        """
        while True:
            try:
                choice = input().strip()

                if choice.lower() in {'q', 'quit', 'exit'}:
                    return None

                try:
                    number = int(choice)
                    if 1 <= number <= max_user_messages:
                        return number
                    else:
                        typer.secho(f"Please enter a number between 1 and {max_user_messages}", fg=typer.colors.RED)
                        typer.secho(f"Select a user message (1-{max_user_messages}) or 'q' to cancel:",
                                   fg=typer.colors.YELLOW, bold=True)
                except ValueError:
                    typer.secho("Please enter a valid number", fg=typer.colors.RED)
                    typer.secho(f"Select a user message (1-{max_user_messages}) or 'q' to cancel:",
                               fg=typer.colors.YELLOW, bold=True)

            except (EOFError, KeyboardInterrupt):
                typer.secho("\nOperation cancelled.", fg=typer.colors.YELLOW)
                return None
