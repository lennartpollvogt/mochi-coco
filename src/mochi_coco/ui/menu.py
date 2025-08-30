from typing import List, Optional
import typer
from ..ollama.client import OllamaClient, ModelInfo
from ..chat.session import ChatSession
from ..rendering import MarkdownRenderer


class ModelSelector:
    def __init__(self, client: OllamaClient, renderer: Optional[MarkdownRenderer] = None):
        self.client = client
        self.renderer = renderer

    def display_models_table(self, models: List[ModelInfo]) -> None:
        """Display available models in a nice table format."""
        if not models:
            typer.secho("No models found!", fg=typer.colors.RED)
            return

        typer.secho("\nAvailable Models:", fg=typer.colors.BRIGHT_GREEN, bold=True)
        typer.echo("=" * 80)

        # Table header
        header = f"{'#':<3} {'Model Name':<30} {'Size (MB)':<12} {'Family':<15}"
        typer.secho(header, fg=typer.colors.CYAN, bold=True)
        typer.echo("-" * 80)

        # Table rows
        for i, model in enumerate(models, 1):
            size_str = f"{model.size_mb:.1f}" if model.size_mb else "N/A"
            family_str = model.family or "N/A"

            row = f"{i:<3} {model.name:<30} {size_str:<12} {family_str:<15}"
            typer.echo(row)

        typer.echo("=" * 80)

    def select_model(self) -> Optional[str]:
        """Display model selection menu and return the selected model name."""
        typer.secho("🤖 Model Selection", fg=typer.colors.BRIGHT_MAGENTA, bold=True)

        try:
            models = self.client.list_models()
        except Exception as e:
            typer.secho(f"Error loading models: {e}", fg=typer.colors.RED)
            return None

        if not models:
            typer.secho("No models available. Please install some models first.", fg=typer.colors.RED)
            return None

        self.display_models_table(models)

        while True:
            try:
                typer.secho(f"\nSelect a model (1-{len(models)}) or 'q' to quit:",
                           fg=typer.colors.YELLOW, bold=True)
                choice = input("Enter your choice: ").strip()

                if choice.lower() in {'q', 'quit', 'exit'}:
                    return None

                index = int(choice) - 1

                if 0 <= index < len(models):
                    selected_model = models[index].name
                    typer.secho(f"\n✅ Selected model: {selected_model}", fg=typer.colors.GREEN, bold=True)
                    return selected_model
                else:
                    typer.secho(f"Please enter a number between 1 and {len(models)}",
                               fg=typer.colors.RED)

            except ValueError:
                typer.secho("Please enter a valid number", fg=typer.colors.RED)
            except (EOFError, KeyboardInterrupt):
                typer.secho("\nExiting model selection.", fg=typer.colors.YELLOW)
                return None

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

    def prompt_markdown_preference(self) -> bool:
        """Prompt user for markdown rendering preference."""
        typer.secho("\n📝 Markdown Rendering", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.secho("Enable markdown formatting for responses?", fg=typer.colors.YELLOW)
        typer.secho("This will format code blocks, headers, tables, etc.", fg=typer.colors.WHITE)

        choice = typer.prompt("Enable markdown? (Y/n)", default="Y", show_default=False)
        return choice.lower() in {"y", "yes", ""}

    def prompt_thinking_display(self) -> bool:
        """Prompt user for thinking block display preference."""
        typer.secho("\n🤔 Thinking Block Display", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.secho("Show model's thinking process in responses?", fg=typer.colors.YELLOW)
        typer.secho("This will display thinking blocks as formatted quotes.", fg=typer.colors.WHITE)

        choice = typer.prompt("Show thinking blocks? (y/N)", default="N", show_default=False)
        return choice.lower() in {"y", "yes"}

    def select_session_or_new(self) -> tuple[Optional[ChatSession], Optional[str], bool, bool]:
        """
        Allow user to select an existing session or start new.
        Returns (session, model_name, markdown_enabled, show_thinking) tuple. If session is None, model_name contains selected model for new chat.
        """
        typer.secho("🚀 Welcome to Mochi-Coco Chat!", fg=typer.colors.BRIGHT_MAGENTA, bold=True)

        # Load existing sessions
        sessions = ChatSession.list_sessions()

        if sessions:
            self.display_sessions_table(sessions)
            typer.secho(f"\nSelect a session (1-{len(sessions)}), type 'new' for new chat, or 'q' to quit:",
                       fg=typer.colors.YELLOW, bold=True)
        else:
            typer.secho("\nNo previous sessions found. Starting new chat...", fg=typer.colors.CYAN)
            selected_model = self.select_model()
            if selected_model:
                markdown_enabled = self.prompt_markdown_preference()
                show_thinking = self.prompt_thinking_display() if markdown_enabled else False
            else:
                markdown_enabled = False
                show_thinking = False
            return None, selected_model, markdown_enabled, show_thinking

        while True:
            try:
                choice = input("Enter your choice: ").strip()

                if choice.lower() in {'q', 'quit', 'exit'}:
                    return None, None, False, False

                if choice.lower() == 'new':
                    selected_model = self.select_model()
                    if selected_model:
                        markdown_enabled = self.prompt_markdown_preference()
                        show_thinking = self.prompt_thinking_display() if markdown_enabled else False
                    else:
                        markdown_enabled = False
                        show_thinking = False
                    return None, selected_model, markdown_enabled, show_thinking

                try:
                    index = int(choice) - 1
                    if 0 <= index < len(sessions):
                        selected_session = sessions[index]

                        # Check if the session's model is still available
                        available_models = [m.name for m in self.client.list_models()]
                        if selected_session.metadata.model not in available_models:
                            typer.secho(f"\n⚠️ Model '{selected_session.metadata.model}' is no longer available.",
                                       fg=typer.colors.RED)
                            typer.secho("Please select a new model:", fg=typer.colors.YELLOW)
                            new_model = self.select_model()
                            if new_model:
                                selected_session.model = new_model
                                selected_session.metadata.model = new_model
                                selected_session.save_session()
                            else:
                                return None, None, False, False

                        typer.secho(f"\n✅ Loaded session: {selected_session.session_id} with {selected_session.metadata.model}",
                                   fg=typer.colors.GREEN, bold=True)
                        markdown_enabled = self.prompt_markdown_preference()
                        show_thinking = self.prompt_thinking_display() if markdown_enabled else False
                        return selected_session, None, markdown_enabled, show_thinking
                    else:
                        typer.secho(f"Please enter a number between 1 and {len(sessions)}, 'new', or 'q'",
                                   fg=typer.colors.RED)
                except ValueError:
                    typer.secho("Please enter a valid number, 'new', or 'q'", fg=typer.colors.RED)

            except (EOFError, KeyboardInterrupt):
                typer.secho("\nExiting.", fg=typer.colors.YELLOW)
                return None, None, False, False

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
