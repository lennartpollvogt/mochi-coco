"""
Chat controller that orchestrates the main chat functionality and manages services.
"""

from typing import Optional, Mapping, Any, List
import typer
import asyncio
import logging

from typing import Optional as OptionalLoop

from .ollama import OllamaClient, AsyncOllamaClient
from .ui import ModelSelector, ChatInterface
from .rendering import MarkdownRenderer, RenderingMode
from .user_prompt import get_user_input
from .commands import CommandProcessor
from .services import SessionManager, RendererManager, SummarizationService

logger = logging.getLogger(__name__)


class ChatController:
    """Main controller that orchestrates the chat application."""

    def __init__(self, host: Optional[str] = None, event_loop: OptionalLoop[asyncio.AbstractEventLoop] = None):
        """
        Initialize the chat controller with all necessary services.

        Args:
            host: Optional Ollama host URL
            event_loop: Event loop for async operations
        """
        # Initialize core components
        self.client = OllamaClient(host=host)
        self.async_client = AsyncOllamaClient(host=host)
        self.renderer = MarkdownRenderer(mode=RenderingMode.PLAIN, show_thinking=False)
        self.model_selector = ModelSelector(self.client, self.renderer)

        # Initialize service layer
        self.renderer_manager = RendererManager(self.renderer)
        self.command_processor = CommandProcessor(self.model_selector, self.renderer_manager)
        self.session_manager = SessionManager(self.model_selector)

        # Initialize chat interface for Rich styling
        self.chat_interface = ChatInterface()

        # Initialize summarization service
        self.summarization_service = SummarizationService(self.async_client)

        # Store event loop for async operations
        self.event_loop = event_loop

        # Initialize session state
        self.session = None
        self.selected_model = None
        self._background_tasks = set()

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

        # Store session state (type assertions are safe here due to the None check above)
        assert session is not None
        assert selected_model is not None
        self.session = session
        self.selected_model = selected_model

        # Start background summarization
        self._start_summarization()

        return True

    def _display_session_info(self) -> None:
        """Display session information and available commands."""
        markdown_enabled = self.renderer_manager.is_markdown_enabled()
        show_thinking = self.renderer_manager.is_thinking_enabled()

        # Display session info using Rich panels
        assert self.session is not None
        assert self.selected_model is not None
        self.chat_interface.print_session_info(
            session_id=self.session.session_id,
            model=self.selected_model,
            markdown=markdown_enabled,
            thinking=show_thinking
        )

        self.chat_interface.print_separator()

    def _run_chat_loop(self) -> None:
        """Run the main chat interaction loop."""
        try:
            while True:
                try:
                    # Use Rich panel for user prompt
                    self.chat_interface.print_user_header()
                    user_input = get_user_input()
                except (EOFError, KeyboardInterrupt):
                    typer.secho("\nExiting.", fg=typer.colors.YELLOW)
                    break

                # Process commands
                if user_input.strip().startswith('/'):
                    # Type assertions are safe here because _initialize_session ensures these are not None
                    assert self.session is not None
                    assert self.selected_model is not None
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
        finally:
            # Stop background services when exiting
            self._stop_summarization()

    def _process_chat_message(self, user_input: str) -> None:
        """
        Process a regular chat message from the user.

        Args:
            user_input: The user's message
        """
        # Add user message to session
        assert self.session is not None
        self.session.add_user_message(content=user_input)

        try:
            # Use Rich panel for assistant response
            self.chat_interface.print_separator()
            self.chat_interface.print_assistant_header()

            # Use renderer for streaming response
            assert self.session is not None
            assert self.selected_model is not None
            messages: List[Mapping[str, Any]] = self.session.get_messages_for_api()
            text_stream = self.client.chat_stream(self.selected_model, messages)
            final_chunk = self.renderer.render_streaming_response(text_stream)

            self.chat_interface.print_separator()  # Extra spacing
            if final_chunk:
                assert self.session is not None
                self.session.add_message(chunk=final_chunk)
            else:
                raise Exception("No response received. Final chunk: {final_chunk}")
        except Exception as e:
            self.chat_interface.print_error_message(f"Error: {e}")

    def _start_summarization(self) -> None:
        """Start background summarization service."""
        if self.session and self.selected_model and self.event_loop:
            # Schedule the coroutine on the event loop from the sync context
            future = asyncio.run_coroutine_threadsafe(
                self.summarization_service.start_monitoring(
                    self.session,
                    self.selected_model,
                    update_callback=self._on_summary_updated
                ),
                self.event_loop
            )
            self._background_tasks.add(future)
            logger.info("Started background summarization")

    def _stop_summarization(self) -> None:
        """Stop background summarization service."""
        # Stop summarization if running
        if self.summarization_service.is_running and self.event_loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.summarization_service.stop_monitoring(),
                    self.event_loop
                )
            except Exception as e:
                logger.error(f"Error stopping summarization: {e}")

        # Cancel any remaining background tasks
        for future in list(self._background_tasks):
            if not future.done():
                future.cancel()
        self._background_tasks.clear()
        logger.info("Stopped background summarization")

    def _on_summary_updated(self, summary: str) -> None:
        """
        Callback called when summary is updated.

        Args:
            summary: The updated summary text
        """
        # For now, we don't display summaries in the terminal to avoid interrupting chat
        # But we could add a command to show the current summary
        logger.debug(f"Summary updated: {summary[:50]}...")
