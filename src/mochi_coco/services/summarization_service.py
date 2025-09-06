import asyncio
from typing import List, Optional, Callable, Mapping, Any
import logging

from ..ollama import AsyncOllamaClient
from ..chat.session import ChatSession

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for background conversation summarization using async Ollama client."""

    def __init__(self, client: AsyncOllamaClient, model: Optional[str] = None):
        """
        Initialize the summarization service.

        Args:
            client: AsyncOllamaClient instance for making requests
            model: Model name for summarization (if None, will use same model as chat)
        """
        self.client = client
        self.model = model
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._last_message_count = 0

    async def start_monitoring(self, session: ChatSession, chat_model: str, update_callback: Optional[Callable[[str], None]] = None):
        """
        Start background monitoring of the chat session for summarization.

        Args:
            session: The chat session to monitor
            chat_model: The model being used for chat (used as fallback if no specific model set)
            update_callback: Optional callback function called when summary is updated
        """
        if self.running:
            logger.warning("Summarization service is already running")
            return

        self.running = True
        self._last_message_count = len(session.messages)

        # Use specified model or fallback to chat model
        summary_model = self.model or chat_model

        self._task = asyncio.create_task(
            self._monitor_session(session, summary_model, update_callback)
        )
        logger.info(f"Started summarization monitoring using model: {summary_model}")

    async def stop_monitoring(self):
        """Stop the background monitoring."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Summarization monitoring stopped")
                pass

    async def generate_summary_now(self, session: ChatSession, model: str) -> Optional[str]:
        """
        Generate a summary immediately for the current conversation.

        Args:
            session: The chat session to summarize
            model: The model to use for summarization

        Returns:
            Generated summary or None if generation failed
        """
        try:
            return await self._generate_summary(session, model)
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return None

    async def _monitor_session(self, session: ChatSession, model: str, update_callback: Optional[Callable[[str], None]]):
        """
        Monitor session for changes and update summaries.

        Args:
            session: The chat session to monitor
            model: The model to use for summarization
            update_callback: Optional callback for summary updates
        """
        while self.running:
            try:
                current_count = len(session.messages)

                # Check if new messages were added and we have at least one exchange
                if (current_count > self._last_message_count and
                    current_count >= 2 and
                    self._should_update_summary(session)):

                    logger.debug(f"Generating summary for {current_count} messages")
                    summary = await self._generate_summary(session, model)

                    if summary:
                        # Update session metadata
                        if hasattr(session, 'metadata') and session.metadata:
                            session.metadata.summary = summary
                            # Update the updated_at timestamp
                            from datetime import datetime
                            session.metadata.updated_at = datetime.now().isoformat()

                        # Save session to persist the summary to JSON file
                        try:
                            session.save_session()
                            logger.info(f"Summary saved to session file: {summary[:100]}...")
                        except Exception as e:
                            logger.error(f"Failed to save session with summary: {e}")

                        # Call update callback if provided (but don't display in terminal by default)
                        if update_callback:
                            try:
                                update_callback(summary)
                            except Exception as e:
                                logger.error(f"Summary update callback failed: {e}")

                    self._last_message_count = current_count

                # Check every few seconds
                await asyncio.sleep(3)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in summarization monitoring: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    def _should_update_summary(self, session: ChatSession) -> bool:
        """
        Determine if summary should be updated based on conversation state.

        Args:
            session: The chat session to check

        Returns:
            True if summary should be updated
        """
        # Update summary if we have at least one complete exchange (user + assistant)
        if len(session.messages) < 2:
            return False

        # Check if last message is from assistant (indicates completed exchange)
        last_message = session.messages[-1]
        return hasattr(last_message, 'role') and last_message.role == 'assistant'

    async def _generate_summary(self, session: ChatSession, model: str) -> Optional[str]:
        """
        Generate a summary of the current conversation.

        Args:
            session: The chat session to summarize
            model: The model to use for summarization

        Returns:
            Generated summary or None if generation failed
        """
        try:
            messages = session.get_messages_for_api()

            # Create summarization prompt
            summary_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that creates concise summaries of conversations. "
                        "Summarize the key points and topics discussed in 1-2 sentences. "
                        "Focus on the main themes and any important conclusions or decisions."
                    )
                },
                {
                    "role": "user",
                    "content": f"Please summarize this conversation:\n\n{self._format_conversation(messages)}"
                }
            ]

            # Generate summary using single (non-streaming) request
            response = await self.client.chat_single(model, summary_prompt)

            if response and response.message and response.message.content:
                return response.message.content.strip()
            else:
                logger.warning("Empty response from summarization model")
                return None

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return None

    def _format_conversation(self, messages: List[Mapping[str, Any]]) -> str:
        """
        Format conversation messages for summarization.

        Args:
            messages: List of message dictionaries from the session

        Returns:
            Formatted conversation string
        """
        formatted = []

        # Use last 10 messages to avoid context overflow and focus on recent conversation
        recent_messages = messages[-10:] if len(messages) > 10 else messages

        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')

            # Clean up content and truncate if too long
            content = content.strip()
            if len(content) > 500:  # Truncate very long messages
                content = content[:500] + "..."

            formatted.append(f"{role.title()}: {content}")

        return "\n".join(formatted)

    @property
    def is_running(self) -> bool:
        """Check if the summarization service is currently running."""
        return self.running and self._task is not None and not self._task.done()
