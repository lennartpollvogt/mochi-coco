"""
Chat controller that orchestrates the main chat functionality and manages services.

This refactored version uses specialized controllers and orchestrators to handle
different concerns, improving maintainability and testability.
"""

from typing import Optional
import asyncio
import logging

from .ollama import OllamaClient, AsyncOllamaClient, AsyncInstructorOllamaClient
from .ui import ModelSelector, ChatUIOrchestrator
from .rendering import MarkdownRenderer, RenderingMode
from .commands import CommandProcessor
from .services import (
    SessionManager, RendererManager, BackgroundServiceManager,
    SystemPromptService, UserPreferenceService, SessionCreationService,
    SummaryModelManager, SessionSetupHelper
)
from .services.session_creation_types import (
    SessionCreationContext, SessionCreationMode, SessionCreationOptions
)
from .controllers import SessionController, CommandResultHandler

logger = logging.getLogger(__name__)


class ChatController:
    """Main application orchestrator - coordinates between specialized controllers."""

    def __init__(self, host: Optional[str] = None,
                 event_loop: Optional[asyncio.AbstractEventLoop] = None):
        # Initialize clients
        self.client = OllamaClient(host=host)
        self.async_client = AsyncOllamaClient(host=host)
        self.instructor_client = AsyncInstructorOllamaClient(host=host)

        # Instance attributes for test compatibility
        self.session = None
        self.selected_model = None

        # Initialize core services
        self.renderer = MarkdownRenderer(mode=RenderingMode.PLAIN, show_thinking=False)
        self.model_selector = ModelSelector(self.client, self.renderer)
        self.renderer_manager = RendererManager(self.renderer)
        self.session_manager = SessionManager(self.model_selector)

        # Initialize session creation services
        self.system_prompt_service = SystemPromptService()
        self.user_preference_service = UserPreferenceService()
        self.session_creation_service = SessionCreationService(
            self.model_selector,
            self.user_preference_service,
            self.system_prompt_service
        )

        # Note: CommandProcessor needs to be initialized after SessionSetupHelper
        # We'll initialize it later after all dependencies are ready
        self.command_processor = None

        # Initialize specialized controllers and orchestrators
        self.ui_orchestrator = ChatUIOrchestrator()
        self.session_controller = SessionController(self.session_manager, self.client)
        self.command_result_handler = CommandResultHandler(self.ui_orchestrator)

        # Initialize summary model manager
        self.summary_model_manager = SummaryModelManager(self.model_selector, self.ui_orchestrator)

        self.background_service_manager = BackgroundServiceManager(
            event_loop, self.instructor_client, self.summary_model_manager
        )

        # Initialize session setup helper
        self.session_setup_helper = SessionSetupHelper(
            self.ui_orchestrator, self.background_service_manager
        )

        # Initialize command processor with session setup helper
        self.command_processor = CommandProcessor(
            self.model_selector, self.renderer_manager, self.session_setup_helper
        )

    def run(self) -> None:
        """Run the main chat application with standardized session creation."""
        try:
            # Use standardized session creation
            options = SessionCreationOptions(
                context=SessionCreationContext.APPLICATION_STARTUP,
                mode=SessionCreationMode.AUTO_DETECT,
                allow_system_prompt_selection=True,
                collect_preferences=True,
                show_welcome_message=True
            )

            result = self.session_creation_service.create_session(options)
            if not result.success:
                self.ui_orchestrator.display_error(result.error_message or "Failed to create session")
                return

            # Ensure we have valid session and model (should be guaranteed when success=True)
            if result.session is None or result.model is None:
                self.ui_orchestrator.display_error("Session creation succeeded but returned invalid data")
                return

            session, model, preferences = result.session, result.model, result.preferences

            # Store for test compatibility
            self.session = session
            self.selected_model = model

            # Configure renderer with collected preferences
            if preferences:
                self.renderer_manager.configure_renderer(
                    preferences.markdown_enabled,
                    preferences.show_thinking
                )

            # Handle session setup using the centralized helper
            setup_success = self.session_setup_helper.setup_session(
                session, model, preferences, show_session_info=True, summary_callback=self._on_summary_updated
            )

            if not setup_success:
                self.ui_orchestrator.display_error("Session setup was cancelled or failed")
                return

            # Display chat history if needed
            self.ui_orchestrator.display_chat_history_if_needed(session, self.model_selector)

            # Run main chat loop
            self._run_chat_loop(session, model)

        finally:
            self.background_service_manager.stop_all_services()

    def _run_chat_loop(self, session, model) -> None:
        """Run the main chat interaction loop."""
        current_session, current_model = session, model

        while True:
            try:
                # Get user input
                user_input = self.ui_orchestrator.get_user_input()
            except (EOFError, KeyboardInterrupt):
                self.ui_orchestrator.display_exit_message()
                break

            # Process commands
            if user_input.strip().startswith('/'):
                # Ensure current session and model are not None before processing commands
                if current_session is None or current_model is None:
                    self.ui_orchestrator.display_error("Invalid session state")
                    break

                if self.command_processor is None:
                    self.ui_orchestrator.display_error("Command processor not initialized")
                    break

                result = self.command_processor.process_command(
                    user_input, current_session, current_model
                )

                state_result = self.command_result_handler.handle_command_result(
                    result, current_session, current_model
                )

                if state_result.should_exit:
                    break

                # Update session and model from state result
                if state_result.session is not None:
                    current_session = state_result.session
                    self.session = current_session  # Update instance attribute
                if state_result.model is not None:
                    current_model = state_result.model
                    self.selected_model = current_model  # Update instance attribute
                continue

            # Skip empty input
            if not user_input.strip():
                continue

            # Process regular message
            self._process_regular_message(current_session, current_model, user_input)

    def _process_regular_message(self, session, model: str, user_input: str) -> None:
        """Process a regular user message."""
        # Display response headers
        self.ui_orchestrator.display_streaming_response_headers()

        # Process message through session controller
        message_result = self.session_controller.process_user_message(
            session, model, user_input, self.renderer
        )

        # Display footer
        self.ui_orchestrator.display_response_footer()

        # Handle result
        if not message_result.success:
            self.ui_orchestrator.display_error(message_result.error_message or "Failed to process message")



    def _on_summary_updated(self, summary: str) -> None:
        """Callback for summary updates."""
        logger.debug(f"Summary updated: {summary[:50]}...")
