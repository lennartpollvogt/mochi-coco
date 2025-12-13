"""
Context Window Service for calculating context usage on-demand.

This service calculates context window usage only when explicitly triggered:
1. Session start/resume
2. User types /status command

The service always uses fresh model information and the current session state.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ollama import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class ContextWindowInfo:
    """Information about context window usage."""

    current_usage: int
    max_context: int
    percentage: float
    has_valid_data: bool
    error_message: Optional[str] = None


class ContextWindowService:
    """Service for calculating context window usage on-demand."""

    def __init__(self, ollama_client: "OllamaClient"):
        """
        Initialize the context window service.

        Args:
            ollama_client: Ollama client for fetching model information
        """
        self.client = ollama_client
        logger.debug("ContextWindowService initialized")

    def calculate_context_usage_on_demand(
        self, session: "ChatSession", current_model: str
    ) -> ContextWindowInfo:
        """
        Calculate context usage on-demand for the current model and session state.

        Only called when:
        1. Session is started/resumed
        2. User types /status command

        Args:
            session: Current chat session with message history
            current_model: Currently selected model

        Returns:
            ContextWindowInfo object with usage data or error information
        """
        logger.debug(
            f"Calculating context usage for session {session.session_id} with model '{current_model}'"
        )

        if not current_model:
            logger.error("Current model is None or empty")
            return self._create_error_info("No model specified")

        try:
            # Get fresh model info from server (no caching)
            max_context = self._get_current_model_context_length(current_model)
            if not max_context:
                logger.warning(
                    f"Unable to get context length for model {current_model}"
                )
                return self._create_error_info("Model context length unavailable")

            # Calculate current usage from session history
            current_usage = self._calculate_current_usage_from_history(session.messages)
            if current_usage is None:
                logger.info(
                    f"No valid context data found in session {session.session_id}"
                )
                return self._create_error_info(
                    "No valid context data in session", max_context
                )

            percentage = (current_usage / max_context) * 100 if max_context > 0 else 0.0

            logger.info(
                f"Context usage calculated: {current_usage}/{max_context} ({percentage:.1f}%)"
            )

            return ContextWindowInfo(
                current_usage=current_usage,
                max_context=max_context,
                percentage=percentage,
                has_valid_data=True,
            )

        except Exception as e:
            logger.error(f"Error calculating context usage: {str(e)}")
            return self._create_error_info(f"Calculation failed: {str(e)}")

    def _get_current_model_context_length(self, model_name: str) -> Optional[int]:
        """
        Retrieve maximum context window from current model information.

        Always fetches fresh model info - no caching needed for on-demand approach.

        Args:
            model_name: Name of the model to get context length for

        Returns:
            Context length in tokens, or None if unavailable
        """
        try:
            logger.debug(f"Fetching fresh model info for '{model_name}'")

            # Get all available models
            models = self.client.list_models()
            if not models:
                logger.warning("No models available from client")
                return None

            # Log available models for debugging
            available_model_names = [model.name for model in models if model.name]
            logger.debug(f"Available models: {available_model_names}")

            # Find the specific model
            target_model = None
            for model in models:
                if model.name == model_name:
                    target_model = model
                    break

            if not target_model:
                logger.warning(
                    f"Model '{model_name}' not found in available models: {available_model_names}"
                )
                return None

            if not target_model.context_length:
                logger.warning(
                    f"Model '{model_name}' has no context_length information"
                )
                return None

            logger.debug(
                f"Found context length {target_model.context_length} for model '{model_name}'"
            )
            return target_model.context_length

        except Exception as e:
            logger.error(
                f"Error fetching model context length for '{model_name}': {str(e)}"
            )
            return None

    def _calculate_current_usage_from_history(self, messages: List) -> Optional[int]:
        """
        Calculate usage from the most recent valid assistant message.

        Simple approach: Find the last assistant message with tool_calls as null,
        then sum eval_count + prompt_eval_count. This represents how much context
        the current model would use to process this conversation history.

        Args:
            messages: List of SessionMessage objects from chat history

        Returns:
            Total context usage in tokens, or None if no valid data found
        """
        if not messages:
            logger.debug("No messages in session history")
            return None

        try:
            # Look for the most recent assistant message with valid context data
            for message in reversed(messages):
                if (
                    hasattr(message, "role")
                    and message.role == "assistant"
                    and hasattr(message, "tool_calls")
                    and message.tool_calls is None
                ):
                    # Check if message has valid context data
                    if (
                        hasattr(message, "eval_count")
                        and hasattr(message, "prompt_eval_count")
                        and message.eval_count is not None
                        and message.prompt_eval_count is not None
                    ):
                        # Validate that the counts are positive integers
                        if (
                            isinstance(message.eval_count, int)
                            and isinstance(message.prompt_eval_count, int)
                            and message.eval_count > 0
                            and message.prompt_eval_count > 0
                        ):
                            total_usage = message.eval_count + message.prompt_eval_count
                            logger.debug(
                                f"Found valid context data: eval_count={message.eval_count}, "
                                f"prompt_eval_count={message.prompt_eval_count}, total={total_usage}"
                            )
                            return total_usage
                        else:
                            logger.debug(
                                f"Invalid context counts in message: "
                                f"eval_count={message.eval_count}, prompt_eval_count={message.prompt_eval_count}"
                            )

            logger.debug("No valid assistant message with context data found")
            return None

        except Exception as e:
            logger.error(f"Error calculating current usage from history: {str(e)}")
            return None

    def _create_error_info(
        self, error_message: str, max_context: int = 0
    ) -> ContextWindowInfo:
        """
        Create error ContextWindowInfo object.

        Args:
            error_message: Description of the error
            max_context: Maximum context if available, defaults to 0

        Returns:
            ContextWindowInfo with error state
        """
        return ContextWindowInfo(
            current_usage=0,
            max_context=max_context,
            percentage=0.0,
            has_valid_data=False,
            error_message=error_message,
        )
