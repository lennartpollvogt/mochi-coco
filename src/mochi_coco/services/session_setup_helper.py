"""
Session setup helper for managing post-creation session configuration.

This module provides a centralized way to handle session setup tasks that need to
happen after session creation but before the user starts chatting, including:
- Summary model selection and configuration
- Session information display
- Background service initialization

The helper ensures consistent behavior across all session creation scenarios:
startup, menu commands, and session switching.
"""

import logging
from typing import Optional, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui import ChatUIOrchestrator
    from ..services import BackgroundServiceManager
    from ..services.user_preference_service import UserPreferences

logger = logging.getLogger(__name__)


class SessionSetupHelper:
    """
    Helper class to handle post-session-creation setup tasks.

    This centralizes the logic for setting up a session after it has been created
    or loaded, ensuring consistent behavior across different session creation flows.
    """

    def __init__(self,
                 ui_orchestrator: "ChatUIOrchestrator",
                 background_service_manager: "BackgroundServiceManager"):
        """
        Initialize the session setup helper.

        Args:
            ui_orchestrator: UI orchestrator for displaying session info
            background_service_manager: Manager for background services
        """
        self.ui_orchestrator = ui_orchestrator
        self.background_service_manager = background_service_manager

    def setup_session(self,
                     session: "ChatSession",
                     model: str,
                     preferences: Optional["UserPreferences"] = None,
                     show_session_info: bool = True,
                     summary_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Perform complete session setup including summary model selection and UI display.

        Args:
            session: The chat session to set up
            model: The model being used for the session
            preferences: User preferences (markdown, thinking blocks, etc.)
            show_session_info: Whether to display the session info panel
            summary_callback: Callback function for summary updates

        Returns:
            True if setup was successful, False if user cancelled or error occurred
        """
        logger.debug(f"Starting session setup for session {session.session_id} with model {model}")

        try:
            # Step 1: Handle summary model selection before displaying session info
            if not self._handle_summary_model_setup(session, model):
                logger.info("Session setup cancelled during summary model selection")
                return False

            # Step 2: Display session information if requested
            if show_session_info:
                self._display_session_info(session, model, preferences)

            # Step 3: Start background services (this should happen after UI display)
            self._start_background_services(session, model, summary_callback)

            logger.info(f"Session setup completed successfully for {session.session_id}")
            return True

        except Exception as e:
            logger.error(f"Session setup failed: {e}", exc_info=True)
            self.ui_orchestrator.display_error(f"Session setup failed: {e}")
            return False

    def _handle_summary_model_setup(self, session: "ChatSession", model: str) -> bool:
        """
        Handle summary model selection if needed.

        Args:
            session: The chat session
            model: The chat model being used

        Returns:
            True if setup successful or not needed, False if user cancelled
        """
        if not self.background_service_manager.summary_model_manager:
            logger.debug("No summary model manager available, skipping summary model setup")
            return True

        summary_manager = self.background_service_manager.summary_model_manager

        # First, validate any existing stored summary model
        if (session.metadata and
            session.metadata.summary_model):

            stored_model = session.metadata.summary_model

            # Check if the stored summary model is still available (installed)
            is_available = summary_manager.is_summary_model_available(session)

            # Check if the stored summary model is supported for summaries
            is_supported = summary_manager.is_model_supported_for_summaries(stored_model)

            if not is_available:
                logger.warning(f"Stored summary model {stored_model} is no longer available")
                # Reset the summary model so user will be prompted to select a new one
                summary_manager.reset_summary_model(session)
            elif not is_supported:
                logger.warning(f"Stored summary model {stored_model} is no longer supported for summaries")
                # Reset the summary model so user will be prompted to select a new one
                summary_manager.reset_summary_model(session)

        # Check if we need to prompt for summary model selection
        needs_selection = summary_manager.needs_summary_model_selection(model, session)
        logger.debug(f"Summary model selection needed: {needs_selection}")

        if needs_selection:
            # Prompt user to select a summary model
            logger.debug("Prompting user for summary model selection")
            selected_model = summary_manager.prompt_for_summary_model(session, model)

            if not selected_model:
                # User cancelled or error occurred
                logger.info("Summary model selection cancelled")
                return False

            logger.info(f"Summary model '{selected_model}' selected for session {session.session_id}")
        else:
            logger.debug("Summary model selection not needed")

        return True

    def _display_session_info(self,
                             session: "ChatSession",
                             model: str,
                             preferences: Optional["UserPreferences"] = None) -> None:
        """
        Display session information panel.

        Args:
            session: The chat session
            model: The model being used
            preferences: User preferences for display settings
        """
        # Extract display preferences or use defaults
        markdown_enabled = preferences.markdown_enabled if preferences else True
        show_thinking = preferences.show_thinking if preferences else False

        logger.debug("Displaying session information")
        self.ui_orchestrator.display_session_setup(
            session, model, markdown_enabled, show_thinking
        )

    def _start_background_services(self, session: "ChatSession", model: str, summary_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Start background services for the session.

        Args:
            session: The chat session
            model: The model being used
            summary_callback: Callback function for summary updates
        """
        logger.debug("Starting background services")

        # Start summarization service with callback
        actual_callback = summary_callback
        if actual_callback is None:
            # Provide a default callback if none specified
            def default_summary_callback(summary: str) -> None:
                logger.debug(f"Summary updated: {summary[:50]}...")
            actual_callback = default_summary_callback

        self.background_service_manager.start_summarization(
            session, model, actual_callback
        )

        logger.debug("Background services started successfully")

    def handle_session_switch(self,
                             old_session: Optional["ChatSession"],
                             new_session: "ChatSession",
                             new_model: str,
                             preferences: Optional["UserPreferences"] = None,
                             display_history: bool = False,
                             summary_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Handle switching from one session to another.

        This is a specialized setup method for when switching between sessions,
        which may require different handling than creating a fresh session.

        Args:
            old_session: The previous session (if any)
            new_session: The new session to switch to
            new_model: The model for the new session
            preferences: User preferences
            display_history: Whether to display the chat history after setup
            summary_callback: Callback function for summary updates

        Returns:
            True if switch was successful, False otherwise
        """
        logger.debug(f"Handling session switch from {old_session.session_id if old_session else 'None'} to {new_session.session_id}")

        # Stop any existing background services
        if old_session:
            logger.debug("Stopping background services for old session")
            self.background_service_manager.stop_all_services()

        # Perform standard session setup
        success = self.setup_session(new_session, new_model, preferences, show_session_info=True, summary_callback=summary_callback)

        if success and display_history and new_session.messages:
            logger.debug("Chat history display will be handled by command processor")

        return success

    def setup_existing_session(self,
                              session: "ChatSession",
                              model: str,
                              preferences: Optional["UserPreferences"] = None,
                              summary_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Set up an existing session that was loaded from storage.

        This handles special cases that might be needed when loading existing sessions,
        such as validating stored summary models or updating metadata.

        Args:
            session: The loaded session
            model: The model for the session
            preferences: User preferences
            summary_callback: Callback function for summary updates

        Returns:
            True if setup successful, False otherwise
        """
        logger.debug(f"Setting up existing session {session.session_id}")

        # Note: Summary model validation is now handled in _handle_summary_model_setup
        # which is called by setup_session, so we don't need to duplicate it here

        # Perform standard setup
        return self.setup_session(session, model, preferences, show_session_info=True, summary_callback=summary_callback)
