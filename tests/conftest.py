"""
Shared pytest fixtures for the mochi-coco test suite.

This module provides common fixtures used across multiple test files,
including temporary directories, mock objects, and sample data.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock
from typing import Dict, Any

from mochi_coco.chat.session import ChatSession


@pytest.fixture
def temp_sessions_dir():
    """
    Create a temporary directory for session files during tests.

    Yields:
        str: Path to the temporary directory
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_chat_response():
    """
    Create a mock ChatResponse object for testing.

    Returns:
        Mock: A mock ChatResponse with realistic structure
    """
    mock_response = Mock()
    mock_response.message = Mock()
    mock_response.message.__getitem__ = lambda self, key: {
        'content': "Hello, how can I help you?"
    }.get(key, "")
    mock_response.message.role = "assistant"
    mock_response.model = "test-model"
    mock_response.eval_count = 100
    mock_response.prompt_eval_count = 50
    mock_response.done = True
    return mock_response


@pytest.fixture
def mock_ollama_client():
    """
    Create a mock OllamaClient for testing without external dependencies.

    Returns:
        Mock: A mock OllamaClient with basic methods
    """
    client = Mock()

    # Mock list_models response
    mock_model = Mock()
    mock_model.name = "test-model"
    mock_model.size_mb = 1000.0
    mock_model.format = "gguf"
    mock_model.family = "llama"
    mock_model.parameter_size = "7B"
    mock_model.quantization_level = "Q4_0"

    client.list_models.return_value = [mock_model]

    # Mock chat_stream response
    def mock_chat_stream(model, messages):
        yield Mock(
            message={'content': "Hello"},
            done=False,
            eval_count=None,
            prompt_eval_count=None
        )
        yield Mock(
            message={'content': " there!"},
            done=False,
            eval_count=None,
            prompt_eval_count=None
        )
        yield Mock(
            message={'content': ""},
            done=True,
            eval_count=50,
            prompt_eval_count=25
        )

    client.chat_stream.side_effect = mock_chat_stream

    return client


@pytest.fixture
def sample_session_data() -> Dict[str, Any]:
    """
    Provide sample session data for testing serialization/deserialization.

    Returns:
        Dict: Sample session data structure
    """
    return {
        "metadata": {
            "session_id": "test123456",
            "model": "test-model",
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T11:00:00",
            "message_count": 2,
            "summary": None
        },
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?",
                "message_id": "user123",
                "timestamp": "2024-01-01T10:30:00"
            },
            {
                "role": "assistant",
                "content": "I'm doing well, thank you!",
                "model": "test-model",
                "message_id": "assist123",
                "timestamp": "2024-01-01T10:31:00",
                "eval_count": 100,
                "prompt_eval_count": 50
            }
        ]
    }


@pytest.fixture
def sample_session_file(temp_sessions_dir, sample_session_data):
    """
    Create a sample session file for testing file operations.

    Args:
        temp_sessions_dir: Temporary directory fixture
        sample_session_data: Sample session data fixture

    Returns:
        Path: Path to the created session file
    """
    session_file = Path(temp_sessions_dir) / "test123456.json"
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(sample_session_data, f, indent=2)
    return session_file


@pytest.fixture
def corrupted_session_file(temp_sessions_dir):
    """
    Create a corrupted session file for testing error handling.

    Args:
        temp_sessions_dir: Temporary directory fixture

    Returns:
        Path: Path to the corrupted session file
    """
    session_file = Path(temp_sessions_dir) / "corrupted123.json"
    with open(session_file, 'w', encoding='utf-8') as f:
        f.write("{ invalid json content without closing brace")
    return session_file


@pytest.fixture
def populated_chat_session(temp_sessions_dir):
    """
    Create a ChatSession with multiple messages for testing.

    Args:
        temp_sessions_dir: Temporary directory fixture

    Returns:
        ChatSession: A session with user and assistant messages
    """
    session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

    # Add some conversation history
    session.add_user_message("Hello, what's the weather like?")

    # Mock an assistant response
    mock_response = Mock()
    mock_response.message = Mock()
    mock_response.message.__getitem__ = lambda self, key: "It's sunny and 75°F today!"
    mock_response.message.role = "assistant"
    mock_response.model = "test-model"
    mock_response.eval_count = 85
    mock_response.prompt_eval_count = 42

    session.add_message(mock_response)
    session.add_user_message("That's great! Any rain expected?")

    return session


@pytest.fixture
def empty_chat_session(temp_sessions_dir):
    """
    Create an empty ChatSession for testing initialization.

    Args:
        temp_sessions_dir: Temporary directory fixture

    Returns:
        ChatSession: An empty session with no messages
    """
    return ChatSession(model="test-model", sessions_dir=temp_sessions_dir)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# Custom assertion helpers
def assert_valid_session_file(session_file_path: Path):
    """
    Assert that a session file exists and contains valid JSON.

    Args:
        session_file_path: Path to the session file to validate

    Raises:
        AssertionError: If file doesn't exist or contains invalid JSON
    """
    assert session_file_path.exists(), f"Session file {session_file_path} does not exist"

    try:
        with open(session_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert 'metadata' in data, "Session file missing 'metadata' key"
        assert 'messages' in data, "Session file missing 'messages' key"
    except json.JSONDecodeError as e:
        raise AssertionError(f"Session file contains invalid JSON: {e}")


def assert_message_equality(msg1, msg2, ignore_fields=None):
    """
    Assert that two messages are equal, optionally ignoring certain fields.

    Args:
        msg1: First message to compare
        msg2: Second message to compare
        ignore_fields: List of fields to ignore in comparison

    Raises:
        AssertionError: If messages are not equal
    """
    ignore_fields = ignore_fields or []

    fields_to_check = ['role', 'content', 'message_id', 'timestamp']
    if hasattr(msg1, 'model'):
        fields_to_check.append('model')
    if hasattr(msg1, 'eval_count'):
        fields_to_check.extend(['eval_count', 'prompt_eval_count'])

    for field in fields_to_check:
        if field in ignore_fields:
            continue

        val1 = getattr(msg1, field, None)
        val2 = getattr(msg2, field, None)
        assert val1 == val2, f"Field '{field}' differs: {val1} != {val2}"
