"""
Command processor for handling special commands in the chat interface.
"""

from typing import Optional, TYPE_CHECKING
import typer

from ..rendering import RenderingMode
from ..utils import re_render_chat_history

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui import ModelSelector
    from ..services import RendererManager


class CommandResult:
    """Result of command execution."""

    def __init__(self, should_continue: bool = True, should_exit: bool = False,
                 new_session: Optional["ChatSession"] = None, new_model: Optional[str] = None):
        self.should_continue = should_continue
        self.should_exit = should_exit
        self.new_session = new_session
        self.new_model = new_model


class CommandProcessor:
    """Handles processing of special commands in the chat interface."""

    def __init__(self, model_selector: "ModelSelector", renderer_manager: "RendererManager"):
        self.model_selector = model_selector
        self.renderer_manager = renderer_manager

    def process_command(self, user_input: str, session: "ChatSession", selected_model: str) -> CommandResult:
        """
        Process a user command and return the result.

        Args:
            user_input: The user's input string
            session: Current chat session
            selected_model: Currently selected model name

        Returns:
            CommandResult indicating what action to take
        """
        command = user_input.strip()

        # Exit commands
        if command.lower() in {"/exit", "/quit", "/q"}:
            typer.secho("Goodbye.", fg=typer.colors.YELLOW)
            return CommandResult(should_continue=False, should_exit=True)

        # Model change command
        if command == "/models":
            return self._handle_models_command(session)

        # Chat session switching command
        if command == "/chats":
            return self._handle_chats_command()

        # Markdown toggle command
        if command == "/markdown":
            return self._handle_markdown_command(session)

        # Thinking toggle command
        if command == "/thinking":
            return self._handle_thinking_command(session)

        # Not a recognized command
        return CommandResult(should_continue=False)

    def _handle_models_command(self, session: "ChatSession") -> CommandResult:
        """Handle the /models command."""
        new_model = self.model_selector.select_model()
        if new_model:
            session.model = new_model
            session.metadata.model = new_model
            session.save_session()
            typer.secho(f"\n✅ Switched to model: {new_model}\n", fg=typer.colors.GREEN, bold=True)
            return CommandResult(new_model=new_model)
        return CommandResult()

    def _handle_chats_command(self) -> CommandResult:
        """Handle the /chats command."""
        typer.secho("\n🔄 Switching chat sessions...\n", fg=typer.colors.BLUE, bold=True)
        new_session, new_model, new_markdown_enabled, new_show_thinking = self.model_selector.select_session_or_new()

        if new_session is None and new_model is None:
            # User cancelled - continue with current session
            typer.secho("Returning to current session.\n", fg=typer.colors.YELLOW)
            return CommandResult()

        # Update renderer settings with new preferences
        self.renderer_manager.configure_renderer(new_markdown_enabled, new_show_thinking)

        if new_session:
            # Switched to existing session
            self.model_selector.display_chat_history(new_session)
            typer.secho(f"\n💬 Switched to session {new_session.session_id} with {new_session.metadata.model}",
                       fg=typer.colors.BRIGHT_GREEN)
            result = CommandResult(new_session=new_session, new_model=new_session.metadata.model)
        elif new_model:
            # Created new session with valid model
            from ..chat import ChatSession
            new_session = ChatSession(model=new_model)
            typer.secho(f"\n💬 New chat started with {new_model}", fg=typer.colors.BRIGHT_GREEN)
            typer.secho(f"Session ID: {new_session.session_id}", fg=typer.colors.CYAN)
            result = CommandResult(new_session=new_session, new_model=new_model)
        else:
            # This shouldn't happen, but handle gracefully
            typer.secho("Error: No session or model selected. Returning to current session.", fg=typer.colors.RED)
            return CommandResult()

        # Show updated preferences
        if new_markdown_enabled:
            typer.secho("Markdown rendering is enabled.", fg=typer.colors.CYAN)
            if new_show_thinking:
                typer.secho("Thinking blocks will be displayed.", fg=typer.colors.CYAN)

        return result

    def _handle_markdown_command(self, session: "ChatSession") -> CommandResult:
        """Handle the /markdown command."""
        # Toggle rendering mode
        new_mode = self.renderer_manager.toggle_markdown_mode()

        status = "enabled" if new_mode == RenderingMode.MARKDOWN else "disabled"
        typer.secho(f"\n✅ Markdown rendering {status}", fg=typer.colors.GREEN, bold=True)

        # Re-render chat history with new mode
        re_render_chat_history(session, self.model_selector)
        return CommandResult()

    def _handle_thinking_command(self, session: "ChatSession") -> CommandResult:
        """Handle the /thinking command."""
        if not self.renderer_manager.can_toggle_thinking():
            typer.secho("\n⚠️ Thinking blocks can only be toggled in markdown mode.", fg=typer.colors.YELLOW)
            typer.secho("Enable markdown first with '/markdown' command.\n", fg=typer.colors.YELLOW)
        else:
            # Toggle thinking blocks
            new_thinking_state = self.renderer_manager.toggle_thinking_display()
            status = "shown" if new_thinking_state else "hidden"
            typer.secho(f"\n✅ Thinking blocks will be {status}", fg=typer.colors.GREEN, bold=True)

            # Re-render chat history with new thinking setting
            re_render_chat_history(session, self.model_selector)
        return CommandResult()
