"""
UI components for collecting user preferences consistently across all session creation contexts.

This module provides standardized interfaces for gathering user preferences like
markdown rendering and thinking block display settings.
"""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from ..services.session_creation_types import SessionCreationContext, UserPreferences


class PreferenceCollectionUI:
    """UI for collecting user preferences consistently across contexts."""

    def __init__(self):
        self.console = Console()

    def ask_markdown_preference(self, context: SessionCreationContext) -> Optional[bool]:
        """Ask user about markdown rendering preference."""
        try:
            message = """📝 Enable markdown formatting for responses?
This will format code blocks, headers, tables, etc."""

            panel = Panel(
                message,
                title="Markdown Rendering",
                style="cyan",
                padding=(0, 1)
            )
            self.console.print(panel)

            return Confirm.ask("Enable markdown?", default=True)

        except (EOFError, KeyboardInterrupt):
            return None

    def ask_thinking_preference(self, context: SessionCreationContext) -> Optional[bool]:
        """Ask user about thinking blocks preference."""
        try:
            message = """🤔 Show model's thinking process in responses?
This will display thinking blocks as formatted quotes."""

            panel = Panel(
                message,
                title="Thinking Block Display",
                style="yellow",
                padding=(0, 1)
            )
            self.console.print(panel)

            return Confirm.ask("Show thinking blocks?", default=False)

        except (EOFError, KeyboardInterrupt):
            return None

    def display_preferences_summary(self, preferences: UserPreferences) -> None:
        """Display a summary of the collected preferences."""

        summary_text = f"""✅ Preferences Set:
• Markdown rendering: {'Enabled' if preferences.markdown_enabled else 'Disabled'}
• Thinking blocks: {'Shown' if preferences.show_thinking else 'Hidden'}"""

        if preferences.selected_system_prompt:
            summary_text += f"\n• System prompt: {preferences.selected_system_prompt}"

        panel = Panel(
            summary_text,
            title="Session Preferences",
            style="green",
            padding=(0, 1)
        )
        self.console.print(panel)
