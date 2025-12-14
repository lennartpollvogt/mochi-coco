"""
Dynamic Context Window Service for intelligent context management.

This service provides dynamic context window management that:
1. Automatically tracks context usage throughout conversations
2. Makes intelligent decisions about when to adjust context windows
3. Handles model changes gracefully
4. Provides optimal context window recommendations

The service maintains backward compatibility with the existing on-demand calculation
while adding dynamic management capabilities.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ollama import OllamaClient

logger = logging.getLogger(__name__)


class ContextDecisionReason(Enum):
    """Reasons for context window decisions."""

    INITIAL_SETUP = "initial_setup"
    USAGE_THRESHOLD = "usage_threshold"
    MODEL_CHANGE = "model_change"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    MANUAL_OVERRIDE = "manual_override"


@dataclass
class ContextWindowDecision:
    """Decision about context window adjustment."""

    should_adjust: bool
    new_context_window: Optional[int]
    reason: ContextDecisionReason
    current_usage: int
    current_percentage: float
    explanation: str


@dataclass
class ContextWindowInfo:
    """Information about context window usage."""

    current_usage: int
    max_context: int
    percentage: float
    has_valid_data: bool
    error_message: Optional[str] = None
    # New fields for dynamic management
    optimal_context: Optional[int] = None
    is_dynamic: bool = False
    last_adjustment: Optional[str] = None


class DynamicContextWindowService:
    """Service for dynamic context window management and on-demand calculation."""

    # Configuration constants
    MAX_USAGE_THRESHOLD = 90.0  # Critical usage threshold requiring immediate expansion
    HIGH_USAGE_THRESHOLD = 85.0  # High usage threshold for expansion
    MODERATE_USAGE_THRESHOLD = 70.0  # Moderate usage threshold
    LOW_USAGE_THRESHOLD = 30.0  # Low usage threshold for optimization
    MIN_USAGE_THRESHOLD = 15.0  # Very low usage threshold for aggressive optimization
    CONTEXT_SAFETY_BUFFER = 0.9  # Use 90% of available context
    MIN_CONTEXT_WINDOW = 2048  # Minimum safe context window
    DEFAULT_FALLBACK_CONTEXT = 4096  # Default fallback when all else fails

    def __init__(self, ollama_client: "OllamaClient"):
        """
        Initialize the dynamic context window service.

        Args:
            ollama_client: Ollama client for fetching model information
        """
        self.client = ollama_client
        logger.debug("DynamicContextWindowService initialized")

    def calculate_context_usage_on_demand(
        self, session: "ChatSession", current_model: str
    ) -> ContextWindowInfo:
        """
        Calculate context usage on-demand for the current model and session state.

        This method maintains backward compatibility with the existing interface
        while adding dynamic management capabilities.

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

            # Calculate optimal context window if dynamic management is enabled
            optimal_context = None
            is_dynamic = False
            last_adjustment = None

            if hasattr(session.metadata, "context_window_config"):
                context_config = session.metadata.context_window_config
                if context_config and context_config.get("dynamic_enabled", False):
                    is_dynamic = True
                    optimal_context = self._calculate_optimal_context_window(
                        current_usage, max_context, session
                    )
                    last_adjustment = context_config.get("last_adjustment")

            logger.info(
                f"Context usage calculated: {current_usage}/{max_context} ({percentage:.1f}%)"
            )

            return ContextWindowInfo(
                current_usage=current_usage,
                max_context=max_context,
                percentage=percentage,
                has_valid_data=True,
                optimal_context=optimal_context,
                is_dynamic=is_dynamic,
                last_adjustment=last_adjustment,
            )

        except Exception as e:
            logger.error(f"Error calculating context usage: {str(e)}")
            return self._create_error_info(f"Calculation failed: {str(e)}")

    def calculate_optimal_context_window(
        self, session: "ChatSession", current_model: str
    ) -> ContextWindowDecision:
        """
        Calculate optimal context window for dynamic management.

        Args:
            session: Current chat session
            current_model: Currently selected model

        Returns:
            ContextWindowDecision with recommendation
        """
        logger.debug(
            f"Calculating optimal context window for session {session.session_id}"
        )

        try:
            # Get model's maximum context
            max_context = self._get_current_model_context_length(current_model)
            if not max_context:
                # Graceful degradation: use fallback strategy
                fallback_context = self._get_fallback_context_window(session)
                logger.warning(
                    f"Model context unavailable for {current_model}, using fallback: {fallback_context}"
                )
                return ContextWindowDecision(
                    should_adjust=True if fallback_context else False,
                    new_context_window=fallback_context,
                    reason=ContextDecisionReason.INITIAL_SETUP,
                    current_usage=0,
                    current_percentage=0.0,
                    explanation=f"Model context unavailable, using fallback: {fallback_context or 'none'}",
                )

            # Get current usage
            current_usage = self._calculate_current_usage_from_history(session.messages)
            if current_usage is None:
                # No usage data yet, use conservative default
                recommended_context = min(max_context, 8192)  # Conservative default
                logger.info(
                    f"Context window: {recommended_context:,} tokens - Starting new conversation"
                )
                return ContextWindowDecision(
                    should_adjust=True,
                    new_context_window=recommended_context,
                    reason=ContextDecisionReason.INITIAL_SETUP,
                    current_usage=0,
                    current_percentage=0.0,
                    explanation=f"Initial setup with conservative context window ({recommended_context:,} tokens)",
                )

            # Get current context window setting from session metadata (safely)
            current_context_window = max_context  # Default to model maximum
            context_config = self._safe_get_context_config(session)
            if context_config and context_config.get("current_window"):
                current_context_window = context_config["current_window"]
                # Validate the retrieved context window
                current_context_window = self._validate_context_window(
                    current_context_window, max_context
                )

            # Calculate percentage against current context window (not model max)
            current_percentage = (
                (current_usage / current_context_window) * 100
                if current_context_window > 0
                else 0.0
            )

            # Make decision based on usage patterns
            decision = self._make_context_decision(
                current_usage=current_usage,
                current_percentage=current_percentage,
                max_context=max_context,
                current_context_window=current_context_window,
                session=session,
            )

            # Log the decision
            if decision.should_adjust:
                if decision.reason == ContextDecisionReason.USAGE_THRESHOLD:
                    logger.info(
                        f"Context window: {decision.new_context_window:,} tokens - Usage at {decision.current_percentage:.1f}%, expanding context window"
                    )
                elif decision.reason == ContextDecisionReason.PERFORMANCE_OPTIMIZATION:
                    if decision.new_context_window < current_context_window:
                        logger.info(
                            f"Context window: {decision.new_context_window:,} tokens - Usage at {decision.current_percentage:.1f}%, optimizing context window"
                        )
                    else:
                        logger.info(
                            f"Context window: {decision.new_context_window:,} tokens - Performance optimization"
                        )
            else:
                logger.debug(
                    f"Context window: {current_context_window:,} tokens - No adjustment needed, usage at {decision.current_percentage:.1f}%"
                )

            return decision

        except Exception as e:
            logger.error(f"Error calculating optimal context window: {str(e)}")
            # Graceful degradation: try fallback strategy
            fallback_context = self._get_fallback_context_window(session)
            return ContextWindowDecision(
                should_adjust=True if fallback_context else False,
                new_context_window=fallback_context,
                reason=ContextDecisionReason.INITIAL_SETUP,
                current_usage=0,
                current_percentage=0.0,
                explanation=f"Calculation failed, using fallback: {fallback_context or 'none'} - {str(e)}",
            )

    def reset_context_window_for_model_change(
        self, session: "ChatSession", old_model: str, new_model: str
    ) -> ContextWindowDecision:
        """
        Reset context window configuration when model changes.

        Args:
            session: Current chat session
            old_model: Previous model name
            new_model: New model name

        Returns:
            ContextWindowDecision for the model change
        """
        logger.info(
            f"Resetting context window for model change: {old_model} -> {new_model}"
        )

        try:
            # Get new model's context length
            new_max_context = self._get_current_model_context_length(new_model)
            if not new_max_context:
                # Graceful degradation: use fallback for new model
                fallback_context = self._get_fallback_context_window(session)
                logger.warning(
                    f"New model context unavailable for {new_model}, using fallback: {fallback_context}"
                )
                return ContextWindowDecision(
                    should_adjust=True if fallback_context else False,
                    new_context_window=fallback_context,
                    reason=ContextDecisionReason.MODEL_CHANGE,
                    current_usage=0,
                    current_percentage=0.0,
                    explanation=f"New model context unavailable, using fallback: {fallback_context or 'none'}",
                )

            # Calculate current usage
            current_usage = self._calculate_current_usage_from_history(session.messages)
            if current_usage is None:
                current_usage = 0

            # For model changes, use conservative approach
            # Start with 50% of new model's capacity or current usage + 50%, whichever is larger
            safety_context = max(
                int(new_max_context * 0.5),
                int(current_usage * 1.5)
                if current_usage > 0
                else self.MIN_CONTEXT_WINDOW,
            )

            # Ensure we don't exceed model limits
            recommended_context = min(
                safety_context, int(new_max_context * self.CONTEXT_SAFETY_BUFFER)
            )
            recommended_context = max(recommended_context, self.MIN_CONTEXT_WINDOW)

            new_percentage = (
                (current_usage / recommended_context) * 100
                if recommended_context > 0
                else 0.0
            )

            logger.info(
                f"Context window: {recommended_context:,} tokens - Model changed to {new_model}, reset context window"
            )
            return ContextWindowDecision(
                should_adjust=True,
                new_context_window=recommended_context,
                reason=ContextDecisionReason.MODEL_CHANGE,
                current_usage=current_usage,
                current_percentage=new_percentage,
                explanation=f"Model changed to {new_model}, adjusted context window to {recommended_context:,} tokens",
            )

        except Exception as e:
            logger.error(
                f"Context window: Error in model change handling from {old_model} to {new_model}: {str(e)}"
            )
            # Graceful degradation: try fallback strategy even on error
            fallback_context = self._get_fallback_context_window(session)
            return ContextWindowDecision(
                should_adjust=True if fallback_context else False,
                new_context_window=fallback_context,
                reason=ContextDecisionReason.MODEL_CHANGE,
                current_usage=0,
                current_percentage=0.0,
                explanation=f"Model change failed, using fallback: {fallback_context or 'none'} - {str(e)}",
            )

    def _make_context_decision(
        self,
        current_usage: int,
        current_percentage: float,
        max_context: int,
        current_context_window: int,
        session: "ChatSession",
    ) -> ContextWindowDecision:
        """
        Make a decision about context window adjustment based on usage patterns.

        Args:
            current_usage: Current token usage
            current_percentage: Current usage percentage
            max_context: Model's maximum context length
            current_context_window: Currently configured context window
            session: Chat session for additional context

        Returns:
            ContextWindowDecision with recommendation
        """
        # High usage - need more context
        current_percentage = current_percentage or 0.0

        # High usage: expand context window with edge case handling
        if current_percentage > self.MAX_USAGE_THRESHOLD:
            # Calculate recommended context based on target usage percentage
            target_usage_percentage = 60.0  # Target 60% usage after expansion
            needed_context = int(current_usage / (target_usage_percentage / 100))

            # Handle edge case: very large context usage
            max_safe_context = int(max_context * self.CONTEXT_SAFETY_BUFFER)
            if needed_context > max_safe_context:
                logger.warning(
                    f"Needed context ({needed_context:,}) exceeds model limits, capping at {max_safe_context:,}"
                )
                recommended_context = max_safe_context
            else:
                recommended_context = needed_context

            # Validate the recommendation
            recommended_context = self._validate_context_window(
                recommended_context, max_context
            )

            if recommended_context > current_context_window:
                return ContextWindowDecision(
                    should_adjust=True,
                    new_context_window=recommended_context,
                    reason=ContextDecisionReason.USAGE_THRESHOLD,
                    current_usage=current_usage,
                    current_percentage=current_percentage,
                    explanation=f"High usage ({current_percentage:.1f}%), expanding context to {recommended_context:,} tokens",
                )

        # Low usage - can reduce context for better performance
        elif current_percentage <= self.LOW_USAGE_THRESHOLD:
            # Only reduce if current window is significantly larger than needed
            # Low usage: optimize context window for performance with validation
            if (
                current_percentage < self.MIN_USAGE_THRESHOLD
                and current_context_window > self.MIN_CONTEXT_WINDOW
            ):
                # Calculate efficient context window
                efficient_context = max(
                    int(current_usage * 2),  # Double current usage for safety
                    self.MIN_CONTEXT_WINDOW,
                )

                # Validate the recommendation
                efficient_context = self._validate_context_window(
                    efficient_context, max_context
                )

                # Only adjust if we can save significant context (at least 25%)
                if efficient_context < current_context_window * 0.75:
                    return ContextWindowDecision(
                        should_adjust=True,
                        new_context_window=efficient_context,
                        reason=ContextDecisionReason.PERFORMANCE_OPTIMIZATION,
                        current_usage=current_usage,
                        current_percentage=current_percentage,
                        explanation=f"Low usage ({current_percentage:.1f}%), optimizing context to {efficient_context:,} tokens",
                    )

        # Current usage is in acceptable range
        return ContextWindowDecision(
            should_adjust=False,
            new_context_window=current_context_window,
            reason=ContextDecisionReason.PERFORMANCE_OPTIMIZATION,
            current_usage=current_usage,
            current_percentage=current_percentage,
            explanation=f"Current usage ({current_percentage:.1f}%) is optimal",
        )

    def _calculate_optimal_context_window(
        self, current_usage: int, max_context: int, session: "ChatSession"
    ) -> int:
        """
        Calculate optimal context window size based on usage patterns.

        Args:
            current_usage: Current token usage
            max_context: Maximum available context
            session: Chat session for additional context

        Returns:
            Recommended context window size
        """
        if current_usage == 0:
            # No usage data, use conservative default
            return min(max_context, 8192)

        # Base calculation on current usage with growth buffer
        base_context = int(current_usage * 1.5)  # 50% growth buffer

        # Ensure we have minimum viable context
        base_context = max(base_context, self.MIN_CONTEXT_WINDOW)

        # Don't exceed model limits (with safety buffer)
        max_safe_context = int(max_context * self.CONTEXT_SAFETY_BUFFER)
        optimal_context = min(base_context, max_safe_context)

        return optimal_context

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

    def _get_fallback_context_window(self, session: "ChatSession") -> Optional[int]:
        """
        Get fallback context window when primary calculation fails.

        Fallback strategy:
        1. Use session's current context window if available and valid
        2. Recover from corrupted metadata
        3. Use default fallback context
        4. Return None if all else fails

        Args:
            session: Current chat session

        Returns:
            Fallback context window size or None
        """
        try:
            # Strategy 1: Use session's current context window
            if session.metadata and hasattr(session.metadata, "context_window_config"):
                try:
                    context_config = session.metadata.context_window_config
                    if context_config and isinstance(context_config, dict):
                        current_window = context_config.get("current_window")
                        if isinstance(current_window, int) and current_window > 0:
                            logger.debug(
                                f"Using session's current context window: {current_window}"
                            )
                            return self._validate_context_window(current_window)
                except (AttributeError, TypeError, KeyError) as e:
                    logger.warning(
                        f"Corrupted context window config, attempting recovery: {str(e)}"
                    )
                    # Strategy 2: Try to recover from corrupted metadata
                    recovered_context = self._recover_from_corrupted_metadata(session)
                    if recovered_context:
                        return recovered_context

            # Strategy 3: Use default fallback
            logger.debug(
                f"Using default fallback context: {self.DEFAULT_FALLBACK_CONTEXT}"
            )
            return self.DEFAULT_FALLBACK_CONTEXT

        except Exception as e:
            logger.error(f"Error in fallback context calculation: {str(e)}")
            # Strategy 4: Last resort fallback
            return self.DEFAULT_FALLBACK_CONTEXT

    def _validate_context_window(
        self, context_window: int, max_context: Optional[int] = None
    ) -> int:
        """
        Validate and sanitize context window value.

        Args:
            context_window: Proposed context window size
            max_context: Maximum allowed context (if known)

        Returns:
            Validated context window size
        """
        try:
            # Ensure positive integer
            if not isinstance(context_window, int) or context_window <= 0:
                logger.warning(
                    f"Invalid context window value: {context_window}, using minimum"
                )
                return self.MIN_CONTEXT_WINDOW

            # Ensure minimum
            if context_window < self.MIN_CONTEXT_WINDOW:
                logger.debug(
                    f"Context window below minimum, adjusting: {context_window} -> {self.MIN_CONTEXT_WINDOW}"
                )
                context_window = self.MIN_CONTEXT_WINDOW

            # Cap at model maximum if known
            if max_context and context_window > max_context:
                safe_max = int(max_context * self.CONTEXT_SAFETY_BUFFER)
                logger.warning(
                    f"Context window exceeds model limit, capping: {context_window} -> {safe_max}"
                )
                context_window = safe_max

            return context_window

        except Exception as e:
            logger.error(f"Error validating context window: {str(e)}")
            return self.MIN_CONTEXT_WINDOW

    def _recover_from_corrupted_metadata(self, session: "ChatSession") -> Optional[int]:
        """
        Attempt to recover from corrupted session metadata.

        Args:
            session: Chat session with potentially corrupted metadata

        Returns:
            Recovered context window size or None
        """
        try:
            # Try to reinitialize context window config
            if session.metadata:
                logger.info("Attempting to recover corrupted context window metadata")

                # Reset to safe defaults
                session.metadata.context_window_config = {
                    "dynamic_enabled": True,
                    "current_window": self.DEFAULT_FALLBACK_CONTEXT,
                    "last_adjustment": None,
                    "adjustment_history": [],
                    "manual_override": False,
                }

                logger.info(
                    f"Successfully recovered metadata with fallback context: {self.DEFAULT_FALLBACK_CONTEXT}"
                )
                return self.DEFAULT_FALLBACK_CONTEXT
            else:
                logger.warning("Session metadata is None, cannot recover")
                return None

        except Exception as e:
            logger.error(f"Failed to recover from corrupted metadata: {str(e)}")
            return None

    def _safe_get_context_config(self, session: "ChatSession") -> Optional[dict]:
        """
        Safely get context window config from session metadata with validation.

        Args:
            session: Chat session

        Returns:
            Context config dict or None if invalid/missing
        """
        try:
            if not session or not session.metadata:
                return None

            if not hasattr(session.metadata, "context_window_config"):
                return None

            config = session.metadata.context_window_config
            if not isinstance(config, dict):
                logger.warning(
                    f"Invalid context config type: {type(config)}, auto-repairing"
                )
                # Auto-repair invalid config
                session.metadata.context_window_config = {
                    "dynamic_enabled": True,
                    "current_window": self.DEFAULT_FALLBACK_CONTEXT,
                    "last_adjustment": None,
                    "adjustment_history": [],
                    "manual_override": False,
                }
                return session.metadata.context_window_config

            # Validate required fields
            required_fields = [
                "dynamic_enabled",
                "current_window",
                "last_adjustment",
                "adjustment_history",
                "manual_override",
            ]
            for field in required_fields:
                if field not in config:
                    logger.warning(
                        f"Missing required field in context config: {field}, auto-repairing"
                    )
                    # Auto-repair missing fields
                    defaults = {
                        "dynamic_enabled": True,
                        "current_window": self.DEFAULT_FALLBACK_CONTEXT,
                        "last_adjustment": None,
                        "adjustment_history": [],
                        "manual_override": False,
                    }
                    config[field] = defaults[field]

            return config

        except Exception as e:
            logger.error(f"Error safely getting context config: {str(e)}")
            return None


# Maintain backward compatibility - alias the new service as the old name
ContextWindowService = DynamicContextWindowService
