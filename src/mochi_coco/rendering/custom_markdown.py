"""
Custom Markdown rendering with customized header styles.

This module provides a custom Markdown class that overrides Rich's default
header rendering behavior to provide more customizable header styles.
"""

from typing import ClassVar
from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import Markdown, MarkdownElement, TextElement, MarkdownContext
from rich.text import Text
from markdown_it.token import Token


class CustomHeading(TextElement):
    """A custom heading with configurable styling."""

    @classmethod
    def create(cls, markdown: 'Markdown', token: Token) -> 'CustomHeading':
        return cls(token.tag)

    def on_enter(self, context: MarkdownContext) -> None:
        self.text = Text()
        context.enter_style(self.style_name)

    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.style_name = f"markdown.{tag}"
        super().__init__()

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        text = self.text

        # Custom rendering based on header level
        if self.tag == "h1":
            # H1: Left-aligned with underline
            text.justify = "left"
            # Add underline using the same character repeated
            underline = "═" * len(text.plain)
            yield text
            yield Text(underline, style="markdown.h1")
        elif self.tag == "h2":
            # H2: Left-aligned with lighter underline
            text.justify = "left"
            underline = "─" * len(text.plain)
            yield Text("")  # Empty line before H2
            yield text
            yield Text(underline, style="markdown.h2")
        elif self.tag == "h3":
            # H3: Left-aligned with prefix
            text.justify = "left"
            prefix = Text("▶ ", style="markdown.h3")
            prefixed_text = Text.assemble(prefix, text)
            yield prefixed_text
        else:
            # H4-H6: Simple left-aligned text
            text.justify = "left"
            yield text


class CustomMarkdown(Markdown):
    """
    Custom Markdown renderer with customized header styles.

    This class overrides Rich's default Markdown behavior to provide
    better header styling that doesn't use center alignment or heavy boxes.
    """

    # Override the elements mapping to use our custom heading
    elements: ClassVar[dict[str, type[MarkdownElement]]] = {
        **Markdown.elements,  # Start with default elements
        "heading_open": CustomHeading,  # Replace heading with our custom one
    }

    def __init__(self, *args, **kwargs):
        """Initialize with same signature as Rich's Markdown."""
        super().__init__(*args, **kwargs)
