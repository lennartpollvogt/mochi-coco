"""
Background service manager for handling async background operations in the chat application.

This module extracts background service management logic from ChatController to improve
separation of concerns and provide better lifecycle management for async services.
"""

import asyncio
import logging
from typing import Optional, Callable, Set, TYPE_CHECKING
from .summarization_service import SummarizationService
from ..ollama import AsyncInstructorOllamaClient

if TYPE_CHECKING:
    from ..chat import ChatSession

logger = logging.getLogger(__name__)


class BackgroundServiceManager:
    """Manages background async services for the chat application."""

    def __init__(self, event_loop: Optional[asyncio.AbstractEventLoop] = None,
                 instructor_client: Optional[AsyncInstructorOllamaClient] = None,
    ):
        self.event_loop = event_loop
        self.instructor_client = instructor_client
        self.summarization_service = SummarizationService(instructor_client) if instructor_client else None
        self._background_tasks: Set = set()

    def start_summarization(self, session: "ChatSession", model: str,
                          update_callback: Callable[[str], None]) -> None:
        """Start background summarization service."""
        if not (self.summarization_service and self.event_loop and session and model):
            return

        future = asyncio.run_coroutine_threadsafe(
            self.summarization_service.start_monitoring(
                session, model, update_callback=update_callback
            ),
            self.event_loop
        )
        self._background_tasks.add(future)
        logger.info("Started background summarization")

    def stop_all_services(self) -> None:
        """Stop all background services gracefully."""
        # Stop summarization service
        if self.summarization_service and self.summarization_service.is_running and self.event_loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.summarization_service.stop_monitoring(),
                    self.event_loop
                )
            except Exception as e:
                logger.error(f"Error stopping summarization: {e}")

        # Cancel remaining background tasks
        for future in list(self._background_tasks):
            if not future.done():
                future.cancel()
        self._background_tasks.clear()
        logger.info("Stopped all background services")

    @property
    def is_running(self) -> bool:
        """Check if any background services are running."""
        return bool(self._background_tasks and any(not f.done() for f in self._background_tasks))
