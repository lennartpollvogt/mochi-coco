import asyncio
from typing import List, Optional, Callable, Mapping, Any, Dict
import logging
from pydantic import BaseModel, Field
import json

from ..ollama import AsyncInstructorOllamaClient
from ..chat.session import ChatSession, SessionMessage, UserMessage, SystemMessage

logger = logging.getLogger(__name__)


class ConversationSummary(BaseModel):
    """Structured summary of the conversation"""

    summary: str = Field(
        ..., description="Summary of the conversation in 2-5 sentences"
    )
    topics: List[str] = Field(
        ..., description="List of topics discussed in the conversation"
    )


class SummarizationService:
    """Service for background conversation summarization using async Ollama client."""

    def __init__(
        self,
        instructor_client: Optional[AsyncInstructorOllamaClient],
        model: Optional[str] = None,
    ):
        """
        Initialize the summarization service.

        Args:
            instructor_client: AsyncInstructorOllamaClient instance for structured responses (optional)
            model: Model name for summarization (if None, will use same model as chat)
        """
        self.instructor_client = instructor_client
        self.model = model
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._last_message_count = 0

    async def start_monitoring(
        self,
        session: ChatSession,
        chat_model: str,
        summary_model: Optional[str] = None,
        update_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Start background monitoring of the chat session for summarization.

        Args:
            session: The chat session to monitor
            chat_model: The model being used for chat (used as fallback if no specific model set)
            summary_model: Optional model to use specifically for summaries
            update_callback: Optional callback function called when summary is updated
        """
        if self.running:
            logger.warning("Summarization service is already running")
            return

        self.running = True
        self._last_message_count = len(session.messages)

        # Determine effective model: summary_model > self.model > chat_model
        effective_model = summary_model or self.model or chat_model

        self._task = asyncio.create_task(
            self._monitor_session(session, chat_model, effective_model, update_callback)
        )
        logger.info(f"Started summarization monitoring using model: {effective_model}")

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

    async def generate_summary_now(
        self, session: ChatSession, chat_model: str, summary_model: Optional[str] = None
    ) -> Optional[dict]:
        """
        Generate a summary immediately for the current conversation.

        Args:
            session: The chat session to summarize
            chat_model: The model being used for chat
            summary_model: Optional model to use specifically for summaries

        Returns:
            Generated summary dict or None if generation failed
        """
        try:
            effective_model = summary_model or self.model or chat_model
            return await self._generate_summary(session, effective_model)
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return None

    async def _monitor_session(
        self,
        session: ChatSession,
        chat_model: str,
        summary_model: str,
        update_callback: Optional[Callable[[str], None]],
    ):
        """
        Monitor session for changes and update summaries.

        Args:
            session: The chat session to monitor
            chat_model: The model being used for chat
            summary_model: The model to use for summarization
            update_callback: Optional callback for summary updates
        """
        while self.running:
            try:
                current_count = len(session.messages)

                # Check if new messages were added and we have at least one exchange
                if (
                    current_count > self._last_message_count
                    and current_count >= 2
                    and self._should_update_summary(session)
                ):
                    logger.debug(f"Generating summary for {current_count} messages")
                    summary = await self._generate_summary(session, summary_model)

                    if summary:
                        # Update session metadata
                        if hasattr(session, "metadata") and session.metadata:
                            session.metadata.summary = summary
                            # Update the updated_at timestamp
                            from datetime import datetime

                            session.metadata.updated_at = datetime.now().isoformat()

                        # Save session to persist the summary to JSON file
                        try:
                            session.save_session()
                            # Extract summary text for logging preview
                            summary_preview = summary.get(
                                "summary", "No summary available"
                            )[:100]
                            logger.info(
                                f"Summary saved to session file: {summary_preview}..."
                            )
                        except Exception as e:
                            logger.error(f"Failed to save session with summary: {e}")

                        # Call update callback if provided (but don't display in terminal by default)
                        if update_callback:
                            try:
                                # Extract summary text from dict for callback
                                summary_str = summary.get(
                                    "summary", "No summary text available"
                                )
                                update_callback(summary_str)
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
        last_message: SessionMessage | UserMessage | SystemMessage = session.messages[
            -1
        ]
        return (
            hasattr(last_message, "role")
            and last_message.role == "assistant"
            and last_message.tool_calls is None
        )

    async def _generate_summary(
        self, session: ChatSession, summary_model: str
    ) -> Optional[dict]:
        """
        Generate a summary of the current conversation.

        Args:
            session: The chat session to summarize
            summary_model: The model to use for summarization

        Returns:
            Generated summary dict or None if generation failed
        """
        try:
            # Check if instructor client is available
            if self.instructor_client is None:
                logger.error(
                    "AsyncInstructorOllamaClient is not available for structured summarization"
                )
                return None

            messages = session.get_messages_for_api()
            current_summary = session.get_session_summary()

            # Create summarization prompt
            summary_prompt = [
                {
                    "role": "user",
                    "content": (
                        "You are a observer that creates concise summaries of conversations in a structured format. "
                        f"Here is the current conversation:\n```\n{self._format_conversation(messages)}\n```\n\n"
                        "Make sure you provide the correct json format by adhering to the provided schema."
                        f"As you will overwrite the current summary, consider it in your response. Current summary: \n```\n{current_summary}\n```"
                    ),
                }
            ]
            # Generate summary using single (non-streaming) request
            response = await self.instructor_client.structured_response(
                summary_model, summary_prompt, format=ConversationSummary
            )

            if response and response.message and response.message.content:
                parsed_summary: Dict[str, Any] = json.loads(response.message.content)
                return parsed_summary
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
        formatted = ""

        # Use last 10 messages to avoid context overflow and focus on recent conversation
        # recent_messages = messages[-10:] if len(messages) > 10 else messages

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Clean up content and truncate if too long
            content = content.strip()
            # if len(content) > 500:  # Truncate very long messages
            # content = content[:500] + "..."

            message = (
                f"<{role.title()}>:\n<content>{content}\n</content>\n</{role.title()}>"
            )
            # add message to formatted
            formatted += message

        # return "\n".join(formatted)
        return formatted

    @property
    def is_running(self) -> bool:
        """Check if the summarization service is currently running."""
        return self.running and self._task is not None and not self._task.done()
