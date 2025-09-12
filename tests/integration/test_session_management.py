"""
Integration tests for session management workflows.

Tests the complete session lifecycle including creation, loading, switching,
and persistence across different components like SessionManager, ChatSession,
and file system operations.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from mochi_coco.chat.session import ChatSession
from mochi_coco.services.session_manager import SessionManager
from mochi_coco.ui import ModelSelector


@pytest.mark.integration
class TestSessionManagementFlow:
    """Integration tests for session management workflows."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create temporary directory for session files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_model_selector(self):
        """Create mock ModelSelector for testing."""
        mock_selector = Mock(spec=ModelSelector)
        mock_selector.client = Mock()
        mock_selector.renderer = Mock()
        mock_selector.menu_display = Mock()
        return mock_selector

    @pytest.fixture
    def session_manager(self, mock_model_selector):
        """Create SessionManager with mock dependencies."""
        # Create a SessionManager but patch the SystemPromptService in tests that use it
        return SessionManager(mock_model_selector)

    @pytest.fixture
    def existing_sessions(self, temp_sessions_dir):
        """Create multiple existing sessions for testing."""
        sessions = []

        # Create session 1 - Recent with multiple messages
        session1 = ChatSession(model="llama3.2:latest", sessions_dir=temp_sessions_dir)
        session1.add_user_message("Hello, how are you?")

        mock_response1 = Mock()
        mock_response1.message = Mock()
        mock_response1.message.__getitem__ = lambda self, key: "I'm doing well, thank you!"
        mock_response1.message.role = "assistant"
        mock_response1.model = "llama3.2:latest"
        mock_response1.eval_count = 95
        mock_response1.prompt_eval_count = 45
        session1.add_message(mock_response1)

        session1.add_user_message("Tell me about Python")
        session1.save_session()
        sessions.append(session1)

        # Create session 2 - Older with single message
        session2 = ChatSession(model="phi3:mini", sessions_dir=temp_sessions_dir)
        session2.add_user_message("What is machine learning?")
        session2.save_session()
        sessions.append(session2)

        # Create session 3 - Empty session
        session3 = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        session3.save_session()
        sessions.append(session3)

        return sessions

    def test_session_initialization_new_session_flow(self, session_manager, mock_model_selector):
        """
        Test complete flow for initializing a new session.

        Tests integration of:
        - SessionManager.initialize_session()
        - ModelSelector interaction
        - User preference handling
        """
        # Mock user selections for new session
        mock_model_selector.select_session_or_new.return_value = (
            None,  # session (None = new)
            "llama3.2:latest",  # selected_model
            True,  # markdown_enabled
            False  # show_thinking
        )

        # Initialize session with mocked system prompt service
        with patch.object(session_manager.system_prompt_service, 'has_system_prompts', return_value=False):
            session, model, markdown, thinking, system_prompt = session_manager.initialize_session()

        # Verify results
        assert session is None  # Should be None for new session
        assert model == "llama3.2:latest"
        assert markdown is True
        assert thinking is False
        assert system_prompt is None  # No system prompt for new session in test

        # Verify ModelSelector was called
        mock_model_selector.select_session_or_new.assert_called_once()

    def test_session_initialization_existing_session_flow(
        self,
        session_manager,
        mock_model_selector,
        existing_sessions,
        temp_sessions_dir
    ):
        """
        Test complete flow for initializing with existing session.

        Tests integration of:
        - SessionManager.initialize_session()
        - Existing session loading
        - Session state restoration
        """
        existing_session = existing_sessions[0]  # Use first session

        # Mock user selection of existing session
        mock_model_selector.select_session_or_new.return_value = (
            existing_session,  # Return the existing session
            existing_session.metadata.model,
            True,  # markdown_enabled
            True   # show_thinking
        )

        # Initialize session with mocked system prompt service
        with patch.object(session_manager.system_prompt_service, 'has_system_prompts', return_value=False):
            session, model, markdown, thinking, system_prompt = session_manager.initialize_session()

        # Verify results
        assert session is not None
        assert session.session_id == existing_session.session_id
        assert model == existing_session.metadata.model
        assert markdown is True
        assert thinking is True
        assert system_prompt is None  # Existing session doesn't need system prompt
        assert len(session.messages) > 0  # Should have existing messages

    def test_session_setup_new_session_creation(self, session_manager, temp_sessions_dir):
        """
        Test session setup flow for creating new session.

        Tests integration of:
        - SessionManager.setup_session()
        - ChatSession creation
        - Initial session state
        """
        # Mock ChatSession creation - patch at the module level where it will be imported
        with patch('mochi_coco.chat.ChatSession') as MockSession:
            mock_session = Mock()
            mock_session.session_id = "new123456"
            mock_session.metadata = Mock()
            mock_session.metadata.model = "test-model"
            MockSession.return_value = mock_session

            # Setup new session
            result_session, result_model = session_manager.setup_session(
                session=None,
                selected_model="test-model"
            )

            # Verify session creation
            assert result_session == mock_session
            assert result_model == "test-model"
            MockSession.assert_called_once_with(model="test-model")

    def test_session_setup_existing_session_continuation(
        self,
        session_manager,
        mock_model_selector,
        existing_sessions
    ):
        """
        Test session setup flow for continuing existing session.

        Tests integration of:
        - SessionManager.setup_session()
        - Existing session handling
        - Chat history display
        """
        existing_session = existing_sessions[0]

        # Setup existing session
        result_session, result_model = session_manager.setup_session(
            session=existing_session,
            selected_model=None  # Should use session's model
        )

        # Verify session continuation
        assert result_session == existing_session
        assert result_model == existing_session.metadata.model

        # Note: Chat history display moved to ChatController._display_session_info()
        # SessionManager.setup_session() no longer displays chat history directly
        # Verify chat history was NOT called from session setup
        mock_model_selector.display_chat_history.assert_not_called()

    def test_session_switching_workflow(
        self,
        session_manager,
        mock_model_selector,
        existing_sessions,
        temp_sessions_dir
    ):
        """
        Test complete session switching workflow.

        Tests integration of:
        - Multiple session loading
        - Session selection UI
        - Session state switching
        - Persistence verification
        """
        session1, session2, session3 = existing_sessions

        # Mock switching from session1 to session2
        mock_model_selector.select_session_or_new.return_value = (
            session2,  # Switch to session2
            session2.metadata.model,
            False,  # Different markdown preference
            False   # Different thinking preference
        )

        # Simulate switching workflow
        with patch.object(session_manager.system_prompt_service, 'has_system_prompts', return_value=False):
            new_session, new_model, markdown, thinking, system_prompt = session_manager.initialize_session()
            final_session, final_model = session_manager.setup_session(new_session, new_model, system_prompt)

        # Verify session switch
        assert final_session.session_id == session2.session_id
        assert final_model == session2.metadata.model
        assert final_session != session1  # Switched from session1

        # Verify session content is intact
        assert len(final_session.messages) == len(session2.messages)
        if session2.messages:
            assert final_session.messages[0].content == session2.messages[0].content

    def test_session_persistence_after_operations(self, temp_sessions_dir, existing_sessions):
        """
        Test that session persistence works correctly after various operations.

        Tests integration of:
        - Session loading
        - Message modification
        - Session saving
        - File system persistence
        """
        session = existing_sessions[0]
        original_message_count = len(session.messages)

        # Perform operations on the session
        session.add_user_message("Additional message after loading")

        mock_response = Mock()
        mock_response.message = Mock()
        mock_response.message.__getitem__ = lambda self, key: "Additional response"
        mock_response.message.role = "assistant"
        mock_response.model = session.metadata.model
        mock_response.eval_count = 85
        mock_response.prompt_eval_count = 40
        session.add_message(mock_response)

        # Verify in-memory state
        assert len(session.messages) == original_message_count + 2
        assert session.metadata.message_count == len(session.messages)

        # Create new session instance and load from file
        fresh_session = ChatSession(
            model="",
            session_id=session.session_id,
            sessions_dir=temp_sessions_dir
        )

        load_result = fresh_session.load_session()

        # Verify persistence
        assert load_result is True
        assert len(fresh_session.messages) == original_message_count + 2
        assert fresh_session.messages[-2].content == "Additional message after loading"
        assert fresh_session.messages[-1].content == "Additional response"
        assert fresh_session.metadata.message_count == len(fresh_session.messages)

    def test_session_error_recovery_flow(
        self,
        session_manager,
        mock_model_selector,
        temp_sessions_dir
    ):
        """
        Test session error recovery when files are corrupted or missing.

        Tests integration of:
        - Corrupted session file handling
        - Fallback behavior
        - Error propagation
        - Session recovery options
        """
        # Create corrupted session file
        corrupted_session_id = "corrupted123"
        corrupted_file = Path(temp_sessions_dir) / f"{corrupted_session_id}.json"

        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json content")

        # Try to load corrupted session
        corrupted_session = ChatSession(
            model="test-model",
            session_id=corrupted_session_id,
            sessions_dir=temp_sessions_dir
        )

        load_result = corrupted_session.load_session()

        # Verify graceful failure
        assert load_result is False
        assert len(corrupted_session.messages) == 0
        assert corrupted_session.metadata.model == "test-model"

        # Mock selector to handle recovery by creating new session
        mock_model_selector.select_session_or_new.return_value = (
            None,  # Fall back to new session
            "recovery-model",
            True,
            False
        )

        # Test recovery flow
        with patch.object(session_manager.system_prompt_service, 'has_system_prompts', return_value=False):
            session, model, markdown, thinking, system_prompt = session_manager.initialize_session()
            final_session, final_model = session_manager.setup_session(session, model, system_prompt)

        # Verify recovery
        assert final_session is not None
        assert final_model == "recovery-model"
        assert len(final_session.messages) == 0  # Fresh start

    def test_concurrent_session_file_operations(self, temp_sessions_dir):
        """
        Test concurrent operations on session files don't cause corruption.

        Tests integration of:
        - Multiple session instances
        - Concurrent file operations
        - Data integrity under concurrent access
        """
        session_id = "concurrent123"

        # Create two instances of the same session
        session1 = ChatSession(model="model1", session_id=session_id, sessions_dir=temp_sessions_dir)
        session2 = ChatSession(model="model2", session_id=session_id, sessions_dir=temp_sessions_dir)

        # Both add messages and save
        session1.add_user_message("Message from instance 1")
        session1.save_session()

        session2.add_user_message("Message from instance 2")
        session2.save_session()

        # Load fresh instance to check final state
        fresh_session = ChatSession(model="", session_id=session_id, sessions_dir=temp_sessions_dir)
        load_result = fresh_session.load_session()

        # Verify file is not corrupted and can be loaded
        assert load_result is True
        assert fresh_session.metadata.model in ["model1", "model2"]
        assert len(fresh_session.messages) >= 1

        # Verify JSON is valid
        session_file = Path(temp_sessions_dir) / f"{session_id}.json"
        with open(session_file, 'r') as f:
            data = json.load(f)  # Should not raise JSONDecodeError
            assert 'metadata' in data
            assert 'messages' in data

    def test_session_metadata_consistency(self, temp_sessions_dir, existing_sessions):
        """
        Test that session metadata remains consistent across operations.

        Tests integration of:
        - Metadata updates during operations
        - Consistency across save/load cycles
        - Timestamp management
        """
        session = existing_sessions[0]
        original_created_at = session.metadata.created_at

        # Perform operation that should update metadata
        with patch('mochi_coco.chat.session.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T15:00:00"
            session.add_user_message("New message for metadata test")

        # Verify metadata was updated
        assert session.metadata.created_at == original_created_at  # Should not change
        assert session.metadata.updated_at == "2024-01-01T15:00:00"  # Should be updated
        assert session.metadata.message_count == len(session.messages)

        # Load session from file and verify metadata consistency
        fresh_session = ChatSession(
            model="",
            session_id=session.session_id,
            sessions_dir=temp_sessions_dir
        )

        assert fresh_session.load_session() is True
        assert fresh_session.metadata.created_at == original_created_at
        assert fresh_session.metadata.updated_at == "2024-01-01T15:00:00"
        assert fresh_session.metadata.message_count == len(fresh_session.messages)

    def test_session_listing_and_management(self, temp_sessions_dir, existing_sessions):
        """
        Test session listing and management operations.

        Tests integration of:
        - Session discovery from file system
        - Session sorting by date
        - Session metadata aggregation
        """
        # List sessions should find all existing sessions
        sessions = ChatSession.list_sessions(temp_sessions_dir)

        # Verify all sessions were found
        assert len(sessions) == len(existing_sessions)

        # Verify sessions are sorted by updated_at (most recent first)
        for i in range(len(sessions) - 1):
            current_time = datetime.fromisoformat(sessions[i].metadata.updated_at)
            next_time = datetime.fromisoformat(sessions[i + 1].metadata.updated_at)
            assert current_time >= next_time

        # Verify session IDs match
        found_ids = {s.session_id for s in sessions}
        expected_ids = {s.session_id for s in existing_sessions}
        assert found_ids == expected_ids

        # Test session deletion
        session_to_delete = sessions[0]
        delete_result = session_to_delete.delete_session()
        assert delete_result is True

        # Verify session was removed
        updated_sessions = ChatSession.list_sessions(temp_sessions_dir)
        assert len(updated_sessions) == len(existing_sessions) - 1
        remaining_ids = {s.session_id for s in updated_sessions}
        assert session_to_delete.session_id not in remaining_ids

    def test_session_summary_generation(self, existing_sessions):
        """
        Test session summary generation for different session states.

        Tests integration of:
        - Summary generation logic
        - Handling of different message types
        - Preview text truncation
        """
        session_with_messages = existing_sessions[0]
        empty_session = existing_sessions[2]

        # Test summary for session with messages
        summary_with_messages = session_with_messages.get_session_summary()
        assert session_with_messages.session_id in summary_with_messages
        assert len(summary_with_messages) > len(session_with_messages.session_id)

        # Test summary for empty session
        summary_empty = empty_session.get_session_summary()
        assert "Empty session" in summary_empty
        assert empty_session.metadata.model in summary_empty

        # Test summary truncation with long message
        long_message_session = ChatSession(model="test-model")
        very_long_message = "A" * 100  # Longer than 50 chars
        long_message_session.add_user_message(very_long_message)

        long_summary = long_message_session.get_session_summary()
        assert "A" * 50 + "..." in long_summary
        assert len(long_summary) < len(very_long_message) + 50  # Should be truncated

    def test_session_user_message_indexing(self, existing_sessions):
        """
        Test user message indexing for editing functionality.

        Tests integration of:
        - User message extraction
        - Index mapping between display and actual positions
        - Mixed message type handling
        """
        session = existing_sessions[0]  # Has mixed user/assistant messages

        # Get user messages with indices
        user_messages = session.get_user_messages_with_indices()

        # Verify indexing
        assert len(user_messages) >= 1

        for display_num, actual_index, message in user_messages:
            assert display_num >= 1  # Display numbers are 1-based
            assert actual_index >= 0  # Actual indices are 0-based
            assert message.role == "user"
            assert session.messages[actual_index] == message

        # Verify display numbers are sequential
        display_numbers = [display_num for display_num, _, _ in user_messages]
        assert display_numbers == list(range(1, len(display_numbers) + 1))
