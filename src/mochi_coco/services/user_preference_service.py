"""
Service for collecting and managing user preferences consistently across all session creation contexts.

This service provides a unified interface for collecting user preferences like markdown rendering
and thinking block display settings, ensuring consistent behavior regardless of entry point.
"""

from typing import Optional

from .session_creation_types import UserPreferences, SessionCreationContext
from ..ui.preference_collection_ui import PreferenceCollectionUI


class UserPreferenceService:
    """Service for collecting and managing user preferences consistently."""

    def __init__(self):
        self.ui = PreferenceCollectionUI()

    def collect_preferences(self, context: SessionCreationContext) -> Optional[UserPreferences]:
        """
        Collect user preferences for chat session.

        Args:
            context: The context in which preferences are being collected

        Returns:
            UserPreferences object or None if cancelled
        """
        try:
            # Collect markdown preference
            markdown_enabled = self._collect_markdown_preference(context)
            if markdown_enabled is None:  # User cancelled
                return None

            # Collect thinking blocks preference
            show_thinking = self._collect_thinking_preference(context, markdown_enabled)
            if show_thinking is None:  # User cancelled
                return None

            return UserPreferences(
                markdown_enabled=markdown_enabled,
                show_thinking=show_thinking
            )

        except (EOFError, KeyboardInterrupt):
            return None

    def get_or_collect_preferences(self, context: SessionCreationContext) -> UserPreferences:
        """
        Get preferences, collecting them if needed.

        For existing sessions, we may want to reuse previous preferences
        or collect new ones based on context.
        """
        # For now, always collect fresh preferences
        # Future enhancement: Remember user's last preferences
        preferences = self.collect_preferences(context)
        if preferences is None:
            # Return sensible defaults if collection was cancelled
            return UserPreferences(markdown_enabled=True, show_thinking=False)
        return preferences

    def _collect_markdown_preference(self, context: SessionCreationContext) -> Optional[bool]:
        """Collect markdown rendering preference."""
        return self.ui.ask_markdown_preference(context)

    def _collect_thinking_preference(self, context: SessionCreationContext,
                                   markdown_enabled: bool) -> Optional[bool]:
        """Collect thinking blocks display preference."""
        if not markdown_enabled:
            # Thinking blocks require markdown mode
            return False

        return self.ui.ask_thinking_preference(context)
