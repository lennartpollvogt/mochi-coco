"""
Renderer manager for handling markdown renderer configuration and preferences.
"""

from typing import TYPE_CHECKING

from ..rendering import RenderingMode

if TYPE_CHECKING:
    from ..rendering import MarkdownRenderer


class RendererManager:
    """Manages markdown renderer configuration and user preferences."""

    def __init__(self, renderer: "MarkdownRenderer"):
        self.renderer = renderer

    def configure_renderer(self, markdown_enabled: bool, show_thinking: bool) -> None:
        """
        Configure the renderer based on user preferences.

        Args:
            markdown_enabled: Whether markdown rendering should be enabled
            show_thinking: Whether thinking blocks should be displayed
        """
        rendering_mode = RenderingMode.MARKDOWN if markdown_enabled else RenderingMode.PLAIN
        self.renderer.set_mode(rendering_mode)
        self.renderer.set_show_thinking(show_thinking)

    def toggle_markdown_mode(self) -> RenderingMode:
        """
        Toggle between markdown and plain text rendering modes.

        Returns:
            The new rendering mode after toggling
        """
        current_mode = self.renderer.mode
        new_mode = RenderingMode.PLAIN if current_mode == RenderingMode.MARKDOWN else RenderingMode.MARKDOWN
        self.renderer.set_mode(new_mode)
        return new_mode

    def toggle_thinking_display(self) -> bool:
        """
        Toggle thinking block display (only works in markdown mode).

        Returns:
            True if thinking blocks are now shown, False otherwise
        """
        if self.renderer.mode == RenderingMode.PLAIN:
            return False

        current_show = self.renderer.show_thinking
        new_show = not current_show
        self.renderer.set_show_thinking(new_show)
        return new_show

    def is_markdown_enabled(self) -> bool:
        """Check if markdown rendering is currently enabled."""
        return self.renderer.mode == RenderingMode.MARKDOWN

    def is_thinking_enabled(self) -> bool:
        """Check if thinking block display is currently enabled."""
        return self.renderer.show_thinking

    def can_toggle_thinking(self) -> bool:
        """Check if thinking blocks can be toggled (requires markdown mode)."""
        return self.renderer.mode == RenderingMode.MARKDOWN
