"""
Comprehensive tests for ChatSession class.

Tests cover session creation, message management, persistence,
editing functionality, and error handling.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from mochi_coco.chat.session import ChatSession, UserMessage, SessionMessage


class TestChatSession:
    """Test suite for ChatSession functionality."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create a temporary directory for session files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_chat_response(self):
        """Create a mock ChatResponse for testing."""
        mock_response = Mock()
        mock_response.message = Mock()
        mock_response.message.__getitem__ = lambda self, key: "Hello, how can I help you?"
        mock_response.message.role = "assistant"
        mock_response.model = "test-model"
        mock_response.eval_count = 100
        mock_response.prompt_eval_count = 50
        return mock_response

    @pytest.fixture
    def sample_session(self, temp_sessions_dir):
        """Create a sample session with some messages."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        session.add_user_message("Hello")
        return session

    def test_session_creation_generates_id(self, temp_sessions_dir):
        """Test that new session generates a valid session ID."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        assert session.session_id is not None
        assert len(session.session_id) == 10
        assert session.model == "test-model"
        assert session.sessions_dir == Path(temp_sessions_dir)

    def test_session_creation_with_provided_id(self, temp_sessions_dir):
        """Test session creation with a specific session ID."""
        session_id = "test123456"
        session = ChatSession(
            model="test-model",
            session_id=session_id,
            sessions_dir=temp_sessions_dir
        )

        assert session.session_id == session_id
        assert session.model == "test-model"

    def test_sessions_directory_created(self, temp_sessions_dir):
        """Test that sessions directory is created if it doesn't exist."""
        non_existent_dir = Path(temp_sessions_dir) / "new_sessions"
        assert not non_existent_dir.exists()

        session = ChatSession(model="test-model", sessions_dir=str(non_existent_dir))

        assert non_existent_dir.exists()
        assert session.sessions_dir == non_existent_dir

    def test_metadata_initialization(self, temp_sessions_dir):
        """Test that session metadata is initialized correctly."""
        with patch('mochi_coco.chat.session.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

            assert session.metadata.session_id == session.session_id
            assert session.metadata.model == "test-model"
            assert session.metadata.created_at == "2024-01-01T12:00:00"
            assert session.metadata.updated_at == "2024-01-01T12:00:00"
            assert session.metadata.message_count == 0

    def test_add_user_message(self, temp_sessions_dir):
        """Test adding a user message to the session."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        session.add_user_message("Hello, world!")

        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello, world!"
        assert session.messages[0].message_id is not None
        assert session.messages[0].timestamp is not None
        assert session.metadata.message_count == 1

    def test_add_user_message_with_custom_id(self, temp_sessions_dir):
        """Test adding a user message with a custom message ID."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        custom_id = "custom123"

        session.add_user_message("Hello", message_id=custom_id)

        assert session.messages[0].message_id == custom_id

    def test_add_assistant_message(self, temp_sessions_dir, mock_chat_response):
        """Test adding an assistant message from ChatResponse."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        session.add_message(mock_chat_response)

        assert len(session.messages) == 1
        assert session.messages[0].role == "assistant"
        assert session.messages[0].content == "Hello, how can I help you?"
        assert session.metadata.message_count == 1

    def test_get_messages_for_api(self, temp_sessions_dir, mock_chat_response):
        """Test conversion of messages to API format."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        session.add_user_message("Hello")
        session.add_message(mock_chat_response)

        api_messages = session.get_messages_for_api()

        assert len(api_messages) == 2
        assert api_messages[0] == {"role": "user", "content": "Hello"}
        assert api_messages[1] == {"role": "assistant", "content": "Hello, how can I help you?"}

    def test_session_persistence_roundtrip(self, temp_sessions_dir, mock_chat_response):
        """Test that session data survives save/load cycle."""
        # Create session with messages
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        session.add_user_message("Hello")
        session.add_message(mock_chat_response)
        original_session_id = session.session_id

        # Save session
        session.save_session()
        assert session.session_file.exists()

        # Load session in new object
        loaded_session = ChatSession(
            model="",
            session_id=original_session_id,
            sessions_dir=temp_sessions_dir
        )

        # Verify data integrity
        assert loaded_session.session_id == original_session_id
        assert loaded_session.metadata.model == "test-model"
        assert len(loaded_session.messages) == 2
        assert loaded_session.messages[0].role == "user"
        assert loaded_session.messages[0].content == "Hello"
        assert loaded_session.messages[1].role == "assistant"
        assert loaded_session.messages[1].content == "Hello, how can I help you?"

    def test_load_nonexistent_session(self, temp_sessions_dir):
        """Test loading a session that doesn't exist."""
        session = ChatSession(
            model="test-model",
            session_id="nonexistent",
            sessions_dir=temp_sessions_dir
        )

        result = session.load_session()

        assert result is False
        assert len(session.messages) == 0

    def test_load_corrupted_session_file(self, temp_sessions_dir):
        """Test graceful handling of corrupted session JSON."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        # Create corrupted JSON file
        with open(session.session_file, 'w') as f:
            f.write("{ invalid json content")

        result = session.load_session()

        assert result is False
        assert len(session.messages) == 0

    def test_session_summary_empty(self, temp_sessions_dir):
        """Test session summary for empty session."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        summary = session.get_session_summary()

        assert "Empty session with test-model" in summary

    def test_session_summary_with_messages(self, temp_sessions_dir):
        """Test session summary with messages."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        long_message = "A" * 60  # Longer than 50 chars
        session.add_user_message(long_message)

        summary = session.get_session_summary()

        assert session.session_id in summary
        assert "A" * 50 + "..." in summary

    def test_edit_message_and_truncate(self, sample_session, mock_chat_response):
        """Test editing a message and truncating subsequent messages."""
        # Add more messages to test truncation
        sample_session.add_message(mock_chat_response)
        sample_session.add_user_message("Second message")
        sample_session.add_message(mock_chat_response)

        assert len(sample_session.messages) == 4

        # Edit the first user message
        sample_session.edit_message_and_truncate(0, "Edited hello")

        # Should only have the edited message
        assert len(sample_session.messages) == 1
        assert sample_session.messages[0].content == "Edited hello"
        assert sample_session.metadata.message_count == 1

    def test_edit_message_invalid_index(self, sample_session):
        """Test editing with invalid message index."""
        with pytest.raises(IndexError):
            sample_session.edit_message_and_truncate(10, "New content")

    def test_edit_non_user_message(self, sample_session, mock_chat_response):
        """Test attempting to edit a non-user message."""
        sample_session.add_message(mock_chat_response)

        with pytest.raises(ValueError, match="Can only edit user messages"):
            sample_session.edit_message_and_truncate(1, "New content")

    def test_get_user_messages_with_indices(self, sample_session, mock_chat_response):
        """Test getting user messages with display and actual indices."""
        sample_session.add_message(mock_chat_response)
        sample_session.add_user_message("Second user message")
        sample_session.add_message(mock_chat_response)

        user_messages = sample_session.get_user_messages_with_indices()

        assert len(user_messages) == 2
        # First user message
        display_num, actual_index, message = user_messages[0]
        assert display_num == 1
        assert actual_index == 0
        assert message.content == "Hello"

        # Second user message
        display_num, actual_index, message = user_messages[1]
        assert display_num == 2
        assert actual_index == 2
        assert message.content == "Second user message"

    def test_delete_session(self, sample_session):
        """Test deleting a session file."""
        # Save the session first
        sample_session.save_session()
        assert sample_session.session_file.exists()

        # Delete it
        result = sample_session.delete_session()

        assert result is True
        assert not sample_session.session_file.exists()

    def test_delete_nonexistent_session(self, temp_sessions_dir):
        """Test deleting a session that doesn't exist."""
        session = ChatSession(
            model="test-model",
            session_id="nonexistent",
            sessions_dir=temp_sessions_dir
        )

        result = session.delete_session()

        assert result is False

    def test_list_sessions_empty_directory(self, temp_sessions_dir):
        """Test listing sessions in empty directory."""
        sessions = ChatSession.list_sessions(temp_sessions_dir)

        assert sessions == []

    def test_list_sessions_with_sessions(self, temp_sessions_dir, mock_chat_response):
        """Test listing multiple sessions."""
        # Create multiple sessions
        session1 = ChatSession(model="model1", sessions_dir=temp_sessions_dir)
        session1.add_user_message("Message 1")
        session1.save_session()

        session2 = ChatSession(model="model2", sessions_dir=temp_sessions_dir)
        session2.add_user_message("Message 2")
        session2.save_session()

        # List sessions
        sessions = ChatSession.list_sessions(temp_sessions_dir)

        assert len(sessions) == 2
        # Should be sorted by updated_at (most recent first)
        session_ids = [s.session_id for s in sessions]
        assert session2.session_id in session_ids
        assert session1.session_id in session_ids

    def test_list_sessions_ignores_corrupted_files(self, temp_sessions_dir):
        """Test that list_sessions ignores corrupted session files."""
        # Create a good session
        session = ChatSession(model="good-model", sessions_dir=temp_sessions_dir)
        session.save_session()

        # Create a corrupted session file
        corrupted_file = Path(temp_sessions_dir) / "corrupted.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json }")

        sessions = ChatSession.list_sessions(temp_sessions_dir)

        # Should only return the good session
        assert len(sessions) == 1
        assert sessions[0].session_id == session.session_id

    def test_concurrent_save_operations(self, temp_sessions_dir):
        """Test that concurrent save operations don't corrupt data."""
        session1 = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        session2 = ChatSession(
            model="test-model",
            session_id=session1.session_id,
            sessions_dir=temp_sessions_dir
        )

        # Both sessions add different messages
        session1.add_user_message("Message from session1")
        session2.add_user_message("Message from session2")

        # Save both (this could cause race conditions in real scenarios)
        session1.save_session()
        session2.save_session()

        # Load fresh session and verify it has valid JSON
        fresh_session = ChatSession(
            model="",
            session_id=session1.session_id,
            sessions_dir=temp_sessions_dir
        )
        result = fresh_session.load_session()

        # Should successfully load without JSON errors
        assert result is True

    def test_user_message_auto_fields(self):
        """Test that UserMessage auto-generates ID and timestamp."""
        with patch('mochi_coco.chat.session.uuid') as mock_uuid, \
             patch('mochi_coco.chat.session.datetime') as mock_datetime:

            mock_uuid.uuid4.return_value = MagicMock()
            mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value="12345678-1234-1234-1234-123456789012")
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            message = UserMessage(content="Test message")

            assert message.message_id == "1234567812"  # First 10 chars after removing dashes
            assert message.timestamp == "2024-01-01T12:00:00"
            assert message.role == "user"

    def test_session_message_auto_fields(self):
        """Test that SessionMessage auto-generates ID and timestamp."""
        with patch('mochi_coco.chat.session.uuid') as mock_uuid, \
             patch('mochi_coco.chat.session.datetime') as mock_datetime:

            mock_uuid.uuid4.return_value = MagicMock()
            mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value="12345678-1234-1234-1234-123456789012")
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            message = SessionMessage(role="assistant", content="Test response")

            assert message.message_id == "1234567812"
            assert message.timestamp == "2024-01-01T12:00:00"

    def test_message_getitem_interface(self):
        """Test that messages support dict-like access."""
        user_msg = UserMessage(content="Hello")
        session_msg = SessionMessage(role="assistant", content="Hi there")

        assert user_msg["content"] == "Hello"
        assert user_msg["role"] == "user"
        assert session_msg["content"] == "Hi there"
        assert session_msg["role"] == "assistant"

    def test_session_file_property(self, temp_sessions_dir):
        """Test that session_file property returns correct path."""
        session = ChatSession(
            model="test-model",
            session_id="test123",
            sessions_dir=temp_sessions_dir
        )

        expected_path = Path(temp_sessions_dir) / "test123.json"
        assert session.session_file == expected_path

    def test_empty_message_content_handling(self, temp_sessions_dir):
        """Test handling of empty message content."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        # Should handle empty content gracefully
        session.add_user_message("")
        session.add_user_message("   ")  # Whitespace only

        assert len(session.messages) == 2
        assert session.messages[0].content == ""
        assert session.messages[1].content == "   "

    def test_metadata_updates_on_message_changes(self, sample_session):
        """Test that metadata is updated when messages change."""
        original_updated_at = sample_session.metadata.updated_at

        # Add another message (should update timestamp)
        with patch('mochi_coco.chat.session.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T13:00:00"
            sample_session.add_user_message("Second message")

        assert sample_session.metadata.message_count == 2
        assert sample_session.metadata.updated_at == "2024-01-01T13:00:00"
        assert sample_session.metadata.updated_at != original_updated_at
