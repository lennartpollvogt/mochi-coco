import sys
from enum import Enum
from typing import Optional, Iterator, Tuple
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.live import Live
import re


class RenderingMode(Enum):
    """Rendering mode for assistant responses."""
    PLAIN = "plain"
    MARKDOWN = "markdown"


class MarkdownRenderer:
    """Handles rendering of assistant responses with optional markdown formatting."""

    def __init__(self, mode: RenderingMode = RenderingMode.PLAIN, show_thinking: bool = False):
        """
        Initialize the renderer.

        Args:
            mode: The rendering mode to use (plain text or markdown)
            show_thinking: Whether to show thinking blocks in markdown mode
        """
        self.mode = mode
        self.show_thinking = show_thinking
        self.console = Console()
        self._accumulated_text = ""

    def _preprocess_thinking_blocks(self, text: str) -> str:
        """
        Preprocess text to handle thinking blocks that might interfere with markdown rendering.
        Either removes or formats <think>...</think> and <thinking>...</thinking> blocks.
        """
        if self.show_thinking:
            # Format thinking blocks as blockquotes using regex with proper capture groups
            def format_thinking_block(match):
                # Extract the content inside the thinking block
                thinking_content = match.group(1).strip()

                # Convert each line to a blockquote line
                lines = thinking_content.split('\n')
                blockquote_lines = ['> 💭 **Thinking:**']
                blockquote_lines.append('>')  # Empty line after header

                for line in lines:
                    if line.strip():
                        blockquote_lines.append('> ' + line.strip())
                    else:
                        blockquote_lines.append('>')  # Empty blockquote line

                return '\n'.join(blockquote_lines) + '\n'

            # Process both <think> and <thinking> variants
            text = re.sub(r'<think>(.*?)</think>', format_thinking_block, text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<thinking>(.*?)</thinking>', format_thinking_block, text, flags=re.DOTALL | re.IGNORECASE)
        else:
            # Remove thinking blocks (both <think> and <thinking> variants)
            # Use re.DOTALL to match across newlines
            text = re.sub(r'<think>\s*.*?\s*</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<thinking>\s*.*?\s*</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Clean up any extra whitespace that might be left
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Multiple empty lines -> double newline
        text = text.strip()

        return text

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
                    # Preprocess to handle thinking blocks
                    processed_text = self._preprocess_thinking_blocks(accumulated_text)
                    live.update(Markdown(processed_text))
                    live.refresh()
                except Exception as e:
                    # Fallback to plain text
                    live.update(Text(accumulated_text))
                    live.refresh()
                    print(f"Warning: Markdown rendering failed: {e}", file=sys.stderr)

        return accumulated_text, context_window

    def render_static_text(self, text: str) -> None:
        """
        Render static text with optional markdown formatting.

        Args:
            text: The complete text to render
        """
        if self.mode == RenderingMode.PLAIN:
            # Plain mode: just print normally
            print(text)
            return

        # Markdown mode: process and render as markdown
        if text.strip():
            try:
                # Preprocess to handle thinking blocks
                processed_text = self._preprocess_thinking_blocks(text)
                markdown = Markdown(processed_text)
                self.console.print(markdown)
            except Exception as e:
                # Fallback to plain text
                print(text)
                print(f"Warning: Markdown rendering failed: {e}", file=sys.stderr)
        else:
            # Empty text, just print as-is
            print(text)

    def set_mode(self, mode: RenderingMode) -> None:
        """
        Change the rendering mode.

        Args:
            mode: The new rendering mode
        """
        self.mode = mode

    def set_show_thinking(self, show: bool) -> None:
        """
        Change whether thinking blocks are shown.

        Args:
            show: Whether to show thinking blocks
        """
        self.show_thinking = show

    def is_markdown_enabled(self) -> bool:
        """Check if markdown rendering is enabled."""
        return self.mode == RenderingMode.MARKDOWN
