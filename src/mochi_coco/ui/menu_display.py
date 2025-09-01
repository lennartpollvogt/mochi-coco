"""
Menu display utilities for formatting and displaying tables and UI elements.
"""

from typing import List, Optional
import typer
from ..ollama import OllamaClient, ModelInfo
from ..chat import ChatSession
from ..rendering import MarkdownRenderer


class MenuDisplay:
    """Handles all table formatting and display logic for the menu system."""

    def __init__(self, renderer: Optional[MarkdownRenderer] = None):
        """
        Initialize the display handler.

        Args:
            renderer: Optional markdown renderer for chat history display
        """
        self.renderer = renderer

    def display_models_table(self, models: List[ModelInfo], client: OllamaClient) -> None:
        """Display available models in a nice table format."""
        if not models:
            typer.secho("No models found!", fg=typer.colors.RED)
            return

        typer.secho("\nAvailable Models:", fg=typer.colors.BRIGHT_GREEN, bold=True)
        typer.echo("=" * 80)

        # Table header
        header = f"{'#':<3} {'Model Name':<30} {'Size (MB)':<12} {'Family':<13} {'Max. Cxt Length':<15}"
        typer.secho(header, fg=typer.colors.CYAN, bold=True)
        typer.echo("-" * 80)

        # Table rows
        for i, model in enumerate(models, 1):
            size_str = f"{model.size_mb:.1f}" if model.size_mb else "N/A"
            family_str = model.family or "N/A"
            model_details = client.show_model_details(model.name) if model.name else False
            if model_details:
                max_context_window = model_details.model_dump()['modelinfo'][f'{family_str}.context_length']
            else:
                max_context_window = "N/A"

            row = f"{i:<3} {model.name:<30} {size_str:<12} {family_str:<13} {max_context_window:<15}"
            typer.echo(row)

        typer.echo("=" * 80)
        typer.secho(
            "ATTENTION: The maximum context length is the supported length of the model but not the actual during the chat session.",
            fg=typer.colors.BRIGHT_MAGENTA, bold=True
        )
        typer.secho(
            "Open Ollama application to set default context length!",
            fg=typer.colors.BRIGHT_MAGENTA, bold=True
        )

    def display_sessions_table(self, sessions: List[ChatSession]) -> None:
        """Display available sessions in a nice table format."""
        if not sessions:
            typer.secho("No previous sessions found!", fg=typer.colors.RED)
            return

        typer.secho("\nPrevious Sessions:", fg=typer.colors.BRIGHT_GREEN, bold=True)
        typer.echo("=" * 100)

        # Table header
        header = f"{'#':<3} {'Session ID':<12} {'Model':<20} {'Preview':<40} {'Messages':<8}"
        typer.secho(header, fg=typer.colors.CYAN, bold=True)
        typer.echo("-" * 100)

        # Table rows
        for i, session in enumerate(sessions, 1):
            preview = session.get_session_summary().split(': ', 1)[1] if ': ' in session.get_session_summary() else "Empty session"
            if len(preview) > 40:
                preview = preview[:37] + "..."

            row = f"{i:<3} {session.session_id:<12} {session.metadata.model:<20} {preview:<40} {session.metadata.message_count:<8}"
            typer.echo(row)

        typer.echo("=" * 100)

    def display_menu_help(self, session_count: int) -> None:
        """Display help text for menu options."""
        typer.secho("\nOptions:", fg=typer.colors.YELLOW, bold=True)
        typer.secho(f"• Select session (1-{session_count})", fg=typer.colors.WHITE)
        typer.secho("• Type 'new' for new chat", fg=typer.colors.WHITE)
        typer.secho("• Type '/delete <number>' to delete a session", fg=typer.colors.WHITE)
        typer.secho("• Type 'q' to quit", fg=typer.colors.WHITE)

    def display_welcome_message(self) -> None:
        """Display the welcome message for the chat application."""
        typer.secho("🚀 Welcome to Mochi-Coco Chat!", fg=typer.colors.BRIGHT_MAGENTA, bold=True)

    def display_chat_history(self, session: ChatSession) -> None:
        """Display the chat history of a session."""
        if not session.messages:
            typer.secho("No previous messages in this session.", fg=typer.colors.CYAN)
            return

        typer.secho(f"\n📜 Chat History (Session: {session.session_id}):", fg=typer.colors.BRIGHT_BLUE, bold=True)
        typer.secho(f"Models used: {session.model}", fg=typer.colors.YELLOW)
        typer.echo("=" * 80)

        for message in session.messages:
            if message.role == "user":
                typer.secho("You:", fg=typer.colors.CYAN, bold=True)
                if self.renderer:
                    self.renderer.render_static_text(message.content)
                else:
                    typer.echo(message.content)
            elif message.role == "assistant":
                assistant_label = "\nAssistant:"
                typer.secho(assistant_label, fg=typer.colors.MAGENTA, bold=True)
                if self.renderer:
                    self.renderer.render_static_text(message.content)
                else:
                    typer.echo(message.content)

            # Add consistent spacing after each message for readability
            print()

        typer.echo("=" * 80)

    def display_model_selection_header(self) -> None:
        """Display header for model selection."""
        typer.secho("🤖 Model Selection", fg=typer.colors.BRIGHT_MAGENTA, bold=True)

    def display_model_selection_prompt(self, model_count: int) -> None:
        """Display prompt for model selection."""
        typer.secho(f"\nSelect a model (1-{model_count}) or 'q' to quit:",
                   fg=typer.colors.YELLOW, bold=True)

    def display_no_sessions_message(self) -> None:
        """Display message when no previous sessions are found."""
        typer.secho("\nNo previous sessions found. Starting new chat...", fg=typer.colors.CYAN)

    def display_model_selected(self, model_name: str) -> None:
        """Display confirmation of model selection."""
        typer.secho(f"\n✅ Selected model: {model_name}", fg=typer.colors.GREEN, bold=True)

    def display_session_loaded(self, session_id: str, model: str) -> None:
        """Display confirmation of session loading."""
        typer.secho(f"\n✅ Loaded session: {session_id} with {model}",
                   fg=typer.colors.GREEN, bold=True)
