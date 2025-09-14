"""
Unified service for all session creation scenarios.

This service provides a single entry point for session creation across all contexts
(startup, menu, session switching, etc.) with consistent behavior and user experience.
"""

from typing import Optional, List
import logging

from .session_creation_types import (
    SessionCreationContext, SessionCreationMode, SessionCreationOptions,
    SessionCreationResult, UserPreferences
)
from .user_preference_service import UserPreferenceService
from .system_prompt_service import SystemPromptService
from ..ui.session_creation_ui import SessionCreationUI

# Import with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui import ModelSelector

logger = logging.getLogger(__name__)


class SessionCreationService:
    """Unified service for all session creation scenarios."""

    def __init__(self, model_selector: "ModelSelector",
                 preference_service: UserPreferenceService,
                 system_prompt_service: SystemPromptService):
        self.model_selector = model_selector
        self.preference_service = preference_service
        self.system_prompt_service = system_prompt_service
        self.ui = SessionCreationUI()

    def create_session(self, options: SessionCreationOptions) -> SessionCreationResult:
        """
        Create or load a session based on the provided options.

        This is the single entry point for all session creation scenarios.
        """
        try:
            logger.info(f"Starting session creation - Context: {options.context}, Mode: {options.mode}")

            # Show welcome message if requested
            if options.show_welcome_message:
                self.ui.display_welcome(options.context)

            # Show session creation start message
            #self.ui.display_session_creation_start(options.context)

            # Handle different creation modes
            if options.mode == SessionCreationMode.NEW_SESSION:
                return self._create_new_session(options)
            elif options.mode == SessionCreationMode.LOAD_EXISTING:
                return self._load_existing_session(options)
            elif options.mode == SessionCreationMode.RESUME_SESSION:
                return self._resume_session(options)
            elif options.mode == SessionCreationMode.AUTO_DETECT:
                return self._auto_detect_and_create(options)
            else:
                # Default to auto-detect
                return self._auto_detect_and_create(options)

        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            return SessionCreationResult(None, None, None, None, False, str(e))

    def _auto_detect_and_create(self, options: SessionCreationOptions) -> SessionCreationResult:
        """Auto-detect the best session creation approach."""
        from ..chat import ChatSession
        existing_sessions = ChatSession.list_sessions()

        if not existing_sessions:
            # No sessions exist - must create new
            self.ui.display_no_sessions_available()
            return self._create_new_session(options)
        else:
            # Sessions exist - let user choose
            return self._handle_session_selection_with_options(existing_sessions, options)

    def _handle_session_selection_with_options(self, sessions: List["ChatSession"],
                                             options: SessionCreationOptions) -> SessionCreationResult:
        """Handle session selection when existing sessions are available."""
        self.ui.display_existing_sessions(sessions)

        choice = self.ui.get_session_choice(len(sessions))

        if choice == "new":
            return self._create_new_session(options)
        elif choice in ["q", "quit", "exit"]:
            return SessionCreationResult(None, None, None, None, False, "User quit")
        elif choice.startswith("delete_"):
            session_index = int(choice.split("_")[1]) - 1
            return self._handle_session_deletion(sessions, session_index, options)
        else:
            # Load existing session
            try:
                session_index = int(choice) - 1
                if 0 <= session_index < len(sessions):
                    return self._load_specific_session(sessions[session_index], options)
                else:
                    return SessionCreationResult(None, None, None, None, False, "Invalid session selection")
            except ValueError:
                return SessionCreationResult(None, None, None, None, False, "Invalid input")

    def _create_new_session(self, options: SessionCreationOptions) -> SessionCreationResult:
        """Create a completely new session."""
        # Select model
        model = self._select_model_for_context(options.context)
        if not model:
            return SessionCreationResult(None, None, None, None, False, "No model selected")

        # Collect user preferences
        preferences = None
        if options.collect_preferences:
            preferences = self.preference_service.collect_preferences(options.context)
            if preferences is None:
                return SessionCreationResult(None, None, None, None, False, "Preference collection cancelled")
        else:
            preferences = UserPreferences(markdown_enabled=True, show_thinking=False)

        # Handle system prompt selection
        system_prompt_content = None
        if options.allow_system_prompt_selection and self.system_prompt_service.has_system_prompts():
            system_prompt_content = self._handle_system_prompt_selection(options.context)

        # Create the session
        from ..chat import ChatSession
        session = ChatSession(model=model)

        # Add system prompt if selected
        if system_prompt_content:
            session.add_system_message(content=system_prompt_content)
            if preferences:
                preferences.selected_system_prompt = "Custom"  # Could be enhanced to track filename

        # Display success message
        self.ui.display_session_creation_success(session, model, options.context)

        logger.info(f"Created new session: {session.session_id}")
        return SessionCreationResult(session, model, preferences, SessionCreationMode.NEW_SESSION, True)

    def _load_existing_session(self, options: SessionCreationOptions) -> SessionCreationResult:
        """Load an existing session."""
        from ..chat import ChatSession
        existing_sessions = ChatSession.list_sessions()
        if not existing_sessions:
            # Fall back to creating new session
            logger.info("No existing sessions found, creating new session")
            self.ui.display_no_sessions_available()
            return self._create_new_session(options)

        return self._handle_session_selection_with_options(existing_sessions, options)

    def _resume_session(self, options: SessionCreationOptions) -> SessionCreationResult:
        """Resume the most recent session or create new if none exists."""
        from ..chat import ChatSession
        existing_sessions = ChatSession.list_sessions()

        if not existing_sessions:
            logger.info("No sessions to resume, creating new session")
            self.ui.display_no_sessions_available()
            return self._create_new_session(options)

        # Get the most recent session (sessions are typically ordered by creation time)
        most_recent_session = existing_sessions[0]  # Assuming first is most recent
        return self._load_specific_session(most_recent_session, options)

    def _load_specific_session(self, session: "ChatSession",
                              options: SessionCreationOptions) -> SessionCreationResult:
        """Load a specific session."""
        # Get existing preferences or collect new ones
        preferences = None
        if options.collect_preferences:
            preferences = self.preference_service.get_or_collect_preferences(options.context)
        else:
            # Use default preferences for existing session
            preferences = UserPreferences(markdown_enabled=True, show_thinking=False)

        # Display success message
        self.ui.display_session_creation_success(session, session.metadata.model, options.context)

        logger.info(f"Loaded existing session: {session.session_id}")
        return SessionCreationResult(session, session.metadata.model, preferences,
                                   SessionCreationMode.LOAD_EXISTING, True)

    def _handle_system_prompt_selection(self, context: SessionCreationContext) -> Optional[str]:
        """Handle system prompt selection for new sessions."""
        from ..ui.system_prompt_menu_handler import SystemPromptSelectionContext

        # Map session creation context to system prompt context
        sp_context = SystemPromptSelectionContext.NEW_SESSION
        if context == SessionCreationContext.MENU_COMMAND:
            sp_context = SystemPromptSelectionContext.FROM_MENU

        from ..ui.system_prompt_menu_handler import SystemPromptMenuHandler
        handler = SystemPromptMenuHandler(self.system_prompt_service)
        return handler.select_system_prompt(sp_context)

    def _select_model_for_context(self, context: SessionCreationContext) -> Optional[str]:
        """Select a model appropriate for the given context."""
        from ..ui.model_menu_handler import ModelSelectionContext

        # Map session creation context to model selection context
        if context == SessionCreationContext.APPLICATION_STARTUP:
            model_context = ModelSelectionContext.NO_SESSIONS
        elif context == SessionCreationContext.MENU_COMMAND:
            model_context = ModelSelectionContext.FROM_SESSION_MENU
        else:
            model_context = ModelSelectionContext.FROM_CHAT

        return self.model_selector.select_model(model_context)

    def _handle_session_deletion(self, sessions: List["ChatSession"], index: int,
                               options: SessionCreationOptions) -> SessionCreationResult:
        """Handle session deletion and continue with selection."""
        if 0 <= index < len(sessions):
            session_to_delete = sessions[index]
            if session_to_delete.delete_session():
                self.ui.display_deletion_success(session_to_delete.session_id)
                # Refresh and continue
                from ..chat import ChatSession
                updated_sessions = ChatSession.list_sessions()
                if updated_sessions:
                    return self._handle_session_selection_with_options(updated_sessions, options)
                else:
                    self.ui.display_no_sessions_available()
                    return self._create_new_session(options)
            else:
                self.ui.display_deletion_error(session_to_delete.session_id)
                return self._handle_session_selection_with_options(sessions, options)
        else:
            return SessionCreationResult(None, None, None, None, False, "Invalid session index for deletion")
