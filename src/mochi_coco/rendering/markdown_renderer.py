import sys
from enum import Enum
from typing import Iterator
from rich.console import Console
from .custom_markdown import CustomMarkdown
from rich.text import Text
from rich.live import Live
import re
from .themes import DEFAULT_THEME
from ollama import ChatResponse


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
        self.console = Console(theme=DEFAULT_THEME)
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
        text_chunks: Iterator[ChatResponse]
    ) -> ChatResponse | None:
        """
        Render a streaming response with optional markdown formatting.

        Args:
            text_chunks: Iterator of (text, context_window) tuples from the LLM

        Returns:
            Tuple of (complete_text, context_window)
        """
        accumulated_text = ""
        final_chunk: ChatResponse | None = None

        if self.mode == RenderingMode.PLAIN:
            # Plain mode: just stream normally
            for chunk in text_chunks:
                if chunk:
                    accumulated_text += chunk.message['content']
                    print(chunk.message['content'], end='', flush=True)

                if chunk.done:
                    chunk.message.content = accumulated_text
                    final_chunk = chunk

            print()  # Final newline
            if final_chunk:
                return final_chunk

        # Markdown mode: use Live for replacement
        with Live(console=self.console, refresh_per_second=60, auto_refresh=False) as live:
            # Stream and collect text
            for chunk in text_chunks:
                if chunk:
                    accumulated_text += chunk.message['content']
                    # Show plain text during streaming
                    live.update(Text(accumulated_text))
                    live.refresh()
                if chunk.done:
                    chunk.message.content = accumulated_text
                    final_chunk = chunk

            # After streaming is complete, replace with markdown
            if accumulated_text.strip():
                try:
                    # Preprocess to handle thinking blocks
                    processed_text = self._preprocess_thinking_blocks(accumulated_text)
                    live.update(CustomMarkdown(processed_text))
                    live.refresh()
                except Exception as e:
                    # Fallback to plain text
                    live.update(Text(accumulated_text))
                    live.refresh()
                    print(f"Warning: Markdown rendering failed: {e}", file=sys.stderr)
            if final_chunk:
                return final_chunk

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
                markdown = CustomMarkdown(processed_text)
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
