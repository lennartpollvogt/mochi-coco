"""
Helper functions for chat functionality.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..chat.session import ChatSession
    from ..ui.menu import ModelSelector


def re_render_chat_history(session: "ChatSession", model_selector: "ModelSelector") -> None:
    """Re-render the current chat history with current renderer settings."""
    # Add visual separation
    print("\n" + "=" * 80)
    print("REFRESHING CHAT HISTORY")
    print("=" * 80)

    # Re-display chat history with current renderer settings
    model_selector.display_chat_history(session)
