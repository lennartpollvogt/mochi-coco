"""
Summary model manager for handling model selection when chat models don't support structured output.

This module manages the logic for detecting when a summary model is needed,
prompting users to select an appropriate model, and storing their choice per session.
"""

import logging
from typing import Optional, List, TYPE_CHECKING

from ..constants import is_model_supported_for_summaries

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui import ModelSelector
    from ..ui.chat_ui_orchestrator import ChatUIOrchestrator
    from ..ollama import ModelInfo

logger = logging.getLogger(__name__)


class SummaryModelManager:
    """
    Manages summary model selection and storage for sessions where the chat model
    doesn't support structured output.
    """

    def __init__(self, model_selector: "ModelSelector", ui_orchestrator: "ChatUIOrchestrator"):
        """
        Initialize the summary model manager.

        Args:
            model_selector: ModelSelector instance for handling model selection UI
            ui_orchestrator: ChatUIOrchestrator instance for displaying messages
        """
        self.model_selector = model_selector
        self.ui_orchestrator = ui_orchestrator

    def needs_summary_model_selection(self, chat_model: str, session: "ChatSession") -> bool:
        """
        Determine if summary model selection is needed.

        Args:
            chat_model: Current chat model name
            session: Chat session to check

        Returns:
            True if user needs to select a summary model, False otherwise
        """
        logger.debug(f"Checking if summary model selection needed for chat_model: {chat_model}")

        # If chat model supports summaries, no need for separate model
        supports_summaries = is_model_supported_for_summaries(chat_model)
        logger.debug(f"Chat model supports summaries: {supports_summaries}")
        if supports_summaries:
            return False

        # Check if session has metadata and summary_model
        has_metadata = session.metadata is not None
        logger.debug(f"Session has metadata: {has_metadata}")

        if has_metadata:
            stored_model = session.metadata.summary_model
            logger.debug(f"Stored summary model: {stored_model}")
            if stored_model:
                # Check if the stored summary model is still supported
                stored_model_supported = is_model_supported_for_summaries(stored_model)
                logger.debug(f"Stored summary model supported: {stored_model_supported}")
                if stored_model_supported:
                    return False
                else:
                    logger.debug(f"Stored summary model '{stored_model}' is not supported, selection needed")

        # Chat model is unsupported and no summary model is stored
        logger.debug("Summary model selection needed")
        return True

    def prompt_for_summary_model(self, session: "ChatSession", chat_model: str) -> Optional[str]:
        """
        Prompt user to select a summary model and store their choice.

        Args:
            session: Chat session to store the selection
            chat_model: Current chat model (for context in UI)

        Returns:
            Selected summary model name or None if user cancelled or error occurred
        """
        try:
            # Display context about why we need a summary model
            self._display_summary_model_context(chat_model)

            # Get filtered models (excluding unsupported ones)
            available_models = self._get_supported_summary_models()
            if not available_models:
                self.ui_orchestrator.display_error(
                    "No models available for summarization. Please install compatible models."
                )
                return None

            # Show model selection with summary-specific context
            selected_model = self._select_summary_model_with_context()

            if selected_model:
                # Store the selection in session metadata
                if session.metadata:
                    session.metadata.summary_model = selected_model
                    # Update timestamp to reflect the change
                    from datetime import datetime
                    session.metadata.updated_at = datetime.now().isoformat()

                    # Save session to persist the choice
                    try:
                        session.save_session()
                        logger.info(f"Summary model '{selected_model}' saved for session {session.session_id}")
                    except Exception as e:
                        logger.error(f"Failed to save summary model selection: {e}")
                        self.ui_orchestrator.display_error("Failed to save summary model selection")
                        return None

                # Display confirmation
                self.ui_orchestrator.display_success_message(
                    f"Summary model set to '{selected_model}' for this session"
                )

            return selected_model

        except Exception as e:
            logger.error(f"Error during summary model selection: {e}")
            self.ui_orchestrator.display_error("Failed to select summary model")
            return None

    def get_effective_summary_model(self, session: "ChatSession", chat_model: str) -> Optional[str]:
        """
        Get the model that should be used for summaries.

        Args:
            session: Chat session to check
            chat_model: Current chat model

        Returns:
            Model name to use for summaries or None if summaries should be disabled
        """
        logger.debug(f"Getting effective summary model for chat_model: {chat_model}")

        # If chat model supports summaries, use it
        supports_summaries = is_model_supported_for_summaries(chat_model)
        logger.debug(f"Chat model supports summaries: {supports_summaries}")
        if supports_summaries:
            logger.debug(f"Using chat model for summaries: {chat_model}")
            return chat_model

        # If session has a stored summary model, use it
        has_metadata = session.metadata is not None
        logger.debug(f"Session has metadata: {has_metadata}")

        if has_metadata:
            stored_model = session.metadata.summary_model
            logger.debug(f"Stored summary model: {stored_model}")
            if stored_model:
                # Check if the stored summary model is still supported
                stored_model_supported = is_model_supported_for_summaries(stored_model)
                logger.debug(f"Stored summary model supported: {stored_model_supported}")
                if stored_model_supported:
                    logger.debug(f"Using stored summary model: {stored_model}")
                    return stored_model
                else:
                    logger.debug(f"Stored summary model '{stored_model}' is not supported, ignoring it")

        # No suitable model available
        logger.debug("No suitable model available for summaries")
        return None

    def is_model_supported_for_summaries(self, model: str) -> bool:
        """
        Check if a model supports structured output for summaries.

        Args:
            model: Model name to check

        Returns:
            True if model supports structured summaries, False otherwise
        """
        return is_model_supported_for_summaries(model)

    def reset_summary_model(self, session: "ChatSession") -> None:
        """
        Reset the summary model for a session (e.g., when chat model changes).

        Args:
            session: Chat session to reset
        """
        if session.metadata:
            session.metadata.summary_model = None
            # Update timestamp
            from datetime import datetime
            session.metadata.updated_at = datetime.now().isoformat()

            try:
                session.save_session()
                logger.info(f"Summary model reset for session {session.session_id}")
            except Exception as e:
                logger.error(f"Failed to reset summary model: {e}")

    def _display_summary_model_context(self, chat_model: str) -> None:
        """Display context about why summary model selection is needed."""
        self.ui_orchestrator.display_info_message(
            f"The current model '{chat_model}' doesn't support structured summarization. "
            "Please select a compatible model to use for generating conversation summaries."
        )

    def _get_supported_summary_models(self) -> List["ModelInfo"]:
        """
        Get list of models that support structured summaries.

        Returns:
            List of supported models
        """
        try:
            # Get all available models from the model selector's client
            all_models = self.model_selector.client.list_models()
            if not all_models:
                return []

            # Filter out unsupported models
            supported_models = [
                model for model in all_models
                if model.name and is_model_supported_for_summaries(model.name)
            ]

            return supported_models

        except Exception as e:
            logger.error(f"Failed to get supported summary models: {e}")
            return []

    def _select_summary_model_with_context(self) -> Optional[str]:
        """
        Show model selection UI with summary-specific context.

        Returns:
            Selected model name or None if cancelled
        """
        # Use the enhanced model selector that filters out unsupported models
        selected_model = self.model_selector.model_menu_handler.select_summary_model()

        return selected_model

    def is_summary_model_available(self, session: "ChatSession") -> bool:
        """
        Check if the stored summary model is still available.

        Args:
            session: Chat session to check

        Returns:
            True if summary model is available, False otherwise
        """
        if not (session.metadata and session.metadata.summary_model):
            return False

        try:
            available_models = self.model_selector.client.list_models()
            if not available_models:
                return False

            available_model_names = [model.name for model in available_models]
            return session.metadata.summary_model in available_model_names

        except Exception as e:
            logger.error(f"Failed to check summary model availability: {e}")
            return False
