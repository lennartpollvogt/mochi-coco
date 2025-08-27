import sys
from enum import Enum
from typing import Optional, Iterator, Tuple
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.live import Live


class RenderingMode(Enum):
    """Rendering mode for assistant responses."""
    PLAIN = "plain"
    MARKDOWN = "markdown"


class MarkdownRenderer:
    """Handles rendering of assistant responses with optional markdown formatting."""

    def __init__(self, mode: RenderingMode = RenderingMode.PLAIN):
        """
        Initialize the renderer.

        Args:
            mode: The rendering mode to use (plain text or markdown)
        """
        self.mode = mode
        self.console = Console()
        self._accumulated_text = ""

    def render_streaming_response(
        self,
        text_chunks: Iterator[Tuple[str, Optional[int]]]
    ) -> Tuple[str, Optional[int]]:
        """
        Render a streaming response with optional markdown formatting.

        Args:
            text_chunks: Iterator of (text, context_window) tuples from the LLM

        Returns:
            Tuple of (complete_text, context_window)
        """
        accumulated_text = ""
        context_window = None

        if self.mode == RenderingMode.PLAIN:
            # Plain mode: just stream normally
            for text_chunk, chunk_context_window in text_chunks:
                if text_chunk:
                    accumulated_text += text_chunk
                    print(text_chunk, end='', flush=True)

                if chunk_context_window is not None:
                    context_window = chunk_context_window

            print()  # Final newline
            return accumulated_text, context_window

        # Markdown mode: use Live for replacement
        with Live(console=self.console, refresh_per_second=60, auto_refresh=False) as live:
            # Stream and collect text
            for text_chunk, chunk_context_window in text_chunks:
                if text_chunk:
                    accumulated_text += text_chunk
                    # Show plain text during streaming
                    live.update(Text(accumulated_text))
                    live.refresh()

                if chunk_context_window is not None:
                    context_window = chunk_context_window

            # After streaming is complete, replace with markdown
            if accumulated_text.strip():
                try:
                    live.update(Markdown(accumulated_text))
                    live.refresh()
                except Exception as e:
                    # Fallback to plain text
                    live.update(Text(accumulated_text))
                    live.refresh()
                    print(f"Warning: Markdown rendering failed: {e}", file=sys.stderr)

        return accumulated_text, context_window




    def set_mode(self, mode: RenderingMode) -> None:
        """
        Change the rendering mode.

        Args:
            mode: The new rendering mode
        """
        self.mode = mode

    def is_markdown_enabled(self) -> bool:
        """Check if markdown rendering is enabled."""
        return self.mode == RenderingMode.MARKDOWN
