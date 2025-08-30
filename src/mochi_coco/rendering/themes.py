"""
Custom themes for markdown rendering.

This module contains theme definitions for customizing the appearance of
markdown elements when rendered with Rich.
"""

from rich.theme import Theme


def get_default_markdown_theme() -> Theme:
    """
    Get the default custom markdown theme.

    Returns:
        Theme: A Rich theme with custom markdown styling
    """
    return Theme({
        "markdown.h1": "bold bright_blue",
        "markdown.h2": "bold cyan",
        "markdown.h3": "bold yellow",
        "markdown.h4": "bold white",
        "markdown.h5": "white",
        "markdown.h6": "dim white",
    })


def get_minimal_markdown_theme() -> Theme:
    """
    Get a minimal markdown theme with subtle styling.

    Returns:
        Theme: A Rich theme with minimal markdown styling
    """
    return Theme({
        "markdown.h1": "bold white",
        "markdown.h2": "bold dim white",
        "markdown.h3": "dim white",
        "markdown.h4": "dim white",
        "markdown.h5": "dim white",
        "markdown.h6": "dim white",
    })


def get_colorful_markdown_theme() -> Theme:
    """
    Get a colorful markdown theme with vibrant styling.

    Returns:
        Theme: A Rich theme with colorful markdown styling
    """
    return Theme({
        "markdown.h1": "bold red on black",
        "markdown.h2": "bold green",
        "markdown.h3": "bold magenta",
        "markdown.h4": "bold blue",
        "markdown.h5": "bold yellow",
        "markdown.h6": "cyan",
    })


# Default theme to use
DEFAULT_THEME = get_default_markdown_theme()
