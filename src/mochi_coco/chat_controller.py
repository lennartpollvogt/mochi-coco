"""
Chat controller that orchestrates the main chat functionality and manages services.
"""

from typing import Optional, Mapping, Any, List
import typer

from .ollama import OllamaClient
from .ui import ModelSelector
from .rendering import MarkdownRenderer, RenderingMode
from .user_prompt import get_user_input
from .commands import CommandProcessor
from .services import SessionManager, RendererManager


class ChatController:
    """Main controller that orchestrates the chat application."""

    def __init__(self, host: Optional[str] = None):
        """
        Initialize the chat controller with all necessary services.

        Args:
            host: Optional Ollama host URL
        """
        # Initialize core components
        self.client = OllamaClient(host=host)
        self.renderer = MarkdownRenderer(mode=RenderingMode.PLAIN, show_thinking=False)
        self.model_selector = ModelSelector(self.client, self.renderer)

        # Initialize service layer
        self.renderer_manager = RendererManager(self.renderer)
        self.command_processor = CommandProcessor(self.model_selector, self.renderer_manager)
        self.session_manager = SessionManager(self.model_selector)

        # Initialize session state
        self.session = None
        self.selected_model = None

    def run(self) -> None:
        """Run the main chat application."""
        # Initialize and setup session
        if not self._initialize_session():
            return

        # Display session info and start chat loop
        self._display_session_info()
        self._run_chat_loop()

    def _initialize_session(self) -> bool:
        """
        Initialize the chat session.

        Returns:
            True if session was successfully initialized, False otherwise
        """
        # Get session and user preferences
        session, selected_model, markdown_enabled, show_thinking = self.session_manager.initialize_session()

        # Configure renderer based on user preferences
        self.renderer_manager.configure_renderer(markdown_enabled, show_thinking)

        # Setup session for chatting
        session, selected_model = self.session_manager.setup_session(session, selected_model)

        if session is None or selected_model is None:
            return False

        # Store session state
        self.session = session
        self.selected_model = selected_model

        return True

    def _display_session_info(self) -> None:
        """Display session information and available commands."""
        markdown_enabled = self.renderer_manager.is_markdown_enabled()
        show_thinking = self.renderer_manager.is_thinking_enabled()
        self.session_manager.display_session_info(markdown_enabled, show_thinking)

    def _run_chat_loop(self) -> None:
        """Run the main chat interaction loop."""
        while True:
            try:
                typer.secho("You:", fg=typer.colors.CYAN, bold=True)
                user_input = get_user_input()
            except (EOFError, KeyboardInterrupt):
                typer.secho("\nExiting.", fg=typer.colors.YELLOW)
                break

            # Process commands
            if user_input.strip().startswith('/'):
                result = self.command_processor.process_command(user_input, self.session, self.selected_model)

                if result.should_exit:
                    break

                if result.should_continue:
                    # Update session and model if command returned new values
                    if result.new_session:
                        self.session = result.new_session
                    if result.new_model:
                        self.selected_model = result.new_model
                    continue

            # Skip empty input
            if not user_input.strip():
                continue

            # Process regular chat message
            self._process_chat_message(user_input)

    def _process_chat_message(self, user_input: str) -> None:
        """
        Process a regular chat message from the user.

        Args:
            user_input: The user's message
        """
        # Add user message to session
        self.session.add_user_message(content=user_input)

        try:
            typer.secho("\nAssistant:", fg=typer.colors.MAGENTA, bold=True)

            # Use renderer for streaming response
            messages: List[Mapping[str, Any]] = self.session.get_messages_for_api()
            text_stream = self.client.chat_stream(self.selected_model, messages)
            final_chunk = self.renderer.render_streaming_response(text_stream)

            print()  # Extra newline for spacing
            if final_chunk:
                self.session.add_message(chunk=final_chunk)
            else:
                raise Exception("No response received. Final chunk: {final_chunk}")
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)
