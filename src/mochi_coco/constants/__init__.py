"""
Shared constants for model compatibility and configuration.

This module centralizes model compatibility definitions to ensure consistency
across different parts of the application.
"""

# Models that don't support structured output for summaries
SUMMARY_UNSUPPORTED_MODELS = {
    'gpt-oss:20b',
    'gpt-oss:120b',
    'qwen3:14b',
    'qwen3:30b'
}


def is_model_supported_for_summaries(model_name: str) -> bool:
    """
    Check if a model supports structured output for summaries.

    Args:
        model_name: Name of the model to check

    Returns:
        True if model supports structured summaries, False otherwise
    """
    return model_name not in SUMMARY_UNSUPPORTED_MODELS
