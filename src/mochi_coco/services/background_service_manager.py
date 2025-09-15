"""
Background service manager for handling async background operations in the chat application.

This module extracts background service management logic from ChatController to improve
separation of concerns and provide better lifecycle management for async services.
"""

import asyncio
import logging
from typing import Optional, Callable, Set, TYPE_CHECKING
from .summarization_service import SummarizationService
from .summary_model_manager import SummaryModelManager
from ..ollama import AsyncInstructorOllamaClient

if TYPE_CHECKING:
    from ..chat import ChatSession

logger = logging.getLogger(__name__)


class BackgroundServiceManager:
    """Manages background async services for the chat application."""

    def __init__(self, event_loop: Optional[asyncio.AbstractEventLoop] = None,
                 instructor_client: Optional[AsyncInstructorOllamaClient] = None,
                 summary_model_manager: Optional[SummaryModelManager] = None,
    ):
        self.event_loop = event_loop
        self.instructor_client = instructor_client
        self.summary_model_manager = summary_model_manager
        self.summarization_service = SummarizationService(instructor_client) if instructor_client else None
        self._background_tasks: Set = set()

    def start_summarization(self, session: "ChatSession", model: str,
                          update_callback: Callable[[str], None]) -> None:
        """Start background summarization service."""
        if not (self.summarization_service and self.event_loop and session and model):
            return

        # Determine the model to use for summaries
        logger.debug(f"Determining summary model for chat model: {model}")
        summary_model = self._get_effective_summary_model(session, model)
        logger.debug(f"Effective summary model determined: {summary_model}")

        # If no suitable model is available, skip summarization
        if summary_model is None:
            logger.info("No suitable model available for summarization, skipping")
            return

        future = asyncio.run_coroutine_threadsafe(
            self.summarization_service.start_monitoring(
                session, model, summary_model=summary_model, update_callback=update_callback
            ),
            self.event_loop
        )
        self._background_tasks.add(future)
        logger.info(f"Started background summarization with model: {summary_model}")

    def stop_all_services(self) -> None:
        """Stop all background services gracefully."""
        # Stop summarization service
        if self.summarization_service and self.summarization_service.is_running and self.event_loop:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.summarization_service.stop_monitoring(),
                    self.event_loop
                )
                # Wait for the service to stop completely before proceeding
                future.result(timeout=10.0)
            except Exception as e:
                logger.error(f"Error stopping summarization: {e}")

        # Cancel remaining background tasks
        for future in list(self._background_tasks):
            if not future.done():
                future.cancel()
        self._background_tasks.clear()
        logger.info("Stopped all background services")

    def _get_effective_summary_model(self, session: "ChatSession", chat_model: str) -> Optional[str]:
        """
        Determine which model to use for summaries.

        Note: Summary model selection should have been handled before this is called.

        Args:
            session: Chat session
            chat_model: Current chat model

        Returns:
            Model to use for summaries or None if summaries should be disabled
        """
        if not self.summary_model_manager:
            # Fallback: use chat model if no manager available
            return chat_model

        # Get the effective summary model (summary model selection should have been handled earlier)
        effective_model = self.summary_model_manager.get_effective_summary_model(session, chat_model)
        logger.debug(f"Effective summary model: {effective_model}")
        return effective_model

    @property
    def is_running(self) -> bool:
        """Check if any background services are running."""
        return bool(self._background_tasks and any(not f.done() for f in self._background_tasks))
