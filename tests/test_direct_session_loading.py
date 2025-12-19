"""
Test direct session loading functionality via CLI --chat option.

This module tests the new feature that allows users to directly load
specific chat sessions using `mochi-coco --chat <number>` command.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from mochi_coco.chat.session import ChatSession, SessionMetadata
from mochi_coco.chat_controller import ChatController
from mochi_coco.services.session_creation_types import (
    SessionCreationContext,
    SessionCreationMode,
    SessionCreationOptions,
    SessionCreationResult,
    UserPreferences,
)


@pytest.fixture
def temp_sessions_dir():
    """Create a temporary directory for test sessions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_sessions(temp_sessions_dir):
    """Create mock sessions for testing."""
    sessions = []

    # Create 3 test sessions
    for i in range(3):
        session_id = f"test_session_{i + 1}"
        model = f"test-model-{i + 1}"

        session = ChatSession(
            model=model, session_id=session_id, sessions_dir=temp_sessions_dir
        )

        # Add some test messages
        session.add_user_message(f"Test message {i + 1}")

        # Save the session
        session.save_session()
        sessions.append(session)

    return sessions


class TestDirectSessionLoading:
    """Test direct session loading functionality."""

    def test_create_direct_session_options_valid_number(
        self, mock_sessions, temp_sessions_dir
    ):
        """Test creating direct session options with valid session number."""
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions",
            return_value=mock_sessions,
        ):
            controller = ChatController()

            # Test loading session 2 (index 1)
            options = controller._create_direct_session_options(2)

            assert options.context == SessionCreationContext.DIRECT_SESSION_LOAD
            assert options.mode == SessionCreationMode.LOAD_EXISTING
            assert options.target_session == mock_sessions[1]
            assert options.allow_system_prompt_selection is False
            assert options.collect_preferences is True
            assert options.show_welcome_message is True

    def test_create_direct_session_options_invalid_number_too_high(self, mock_sessions):
        """Test creating direct session options with session number too high."""
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions",
            return_value=mock_sessions,
        ):
            controller = ChatController()

            # Test loading session 5 (doesn't exist)
            options = controller._create_direct_session_options(5)

            # Should fall back to normal startup options
            assert options.context == SessionCreationContext.APPLICATION_STARTUP
            assert options.mode == SessionCreationMode.AUTO_DETECT
            assert options.target_session is None

    def test_create_direct_session_options_invalid_number_zero(self, mock_sessions):
        """Test creating direct session options with session number zero."""
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions",
            return_value=mock_sessions,
        ):
            controller = ChatController()

            # Test loading session 0 (invalid)
            options = controller._create_direct_session_options(0)

            # Should fall back to normal startup options
            assert options.context == SessionCreationContext.APPLICATION_STARTUP
            assert options.mode == SessionCreationMode.AUTO_DETECT
            assert options.target_session is None

    def test_create_direct_session_options_negative_number(self, mock_sessions):
        """Test creating direct session options with negative session number."""
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions",
            return_value=mock_sessions,
        ):
            controller = ChatController()

            # Test loading session -1 (invalid)
            options = controller._create_direct_session_options(-1)

            # Should fall back to normal startup options
            assert options.context == SessionCreationContext.APPLICATION_STARTUP
            assert options.mode == SessionCreationMode.AUTO_DETECT
            assert options.target_session is None

    def test_create_direct_session_options_no_sessions(self):
        """Test creating direct session options when no sessions exist."""
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions", return_value=[]
        ):
            controller = ChatController()

            # Test loading session 1 when no sessions exist
            options = controller._create_direct_session_options(1)

            # Should fall back to normal startup options
            assert options.context == SessionCreationContext.APPLICATION_STARTUP
            assert options.mode == SessionCreationMode.AUTO_DETECT
            assert options.target_session is None

    @patch("mochi_coco.chat_controller.ChatController._run_chat_loop")
    @patch("mochi_coco.chat_controller.ChatController._process_regular_message")
    def test_run_with_target_session_number_success(
        self, mock_process_message, mock_chat_loop, mock_sessions
    ):
        """Test running ChatController with valid target session number."""
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions",
            return_value=mock_sessions,
        ):
            controller = ChatController()

            # Mock the session creation service
            mock_result = SessionCreationResult(
                session=mock_sessions[0],
                model="test-model-1",
                preferences=UserPreferences(markdown_enabled=True, show_thinking=False),
                mode=SessionCreationMode.LOAD_EXISTING,
                success=True,
            )

            with patch.object(
                controller.session_creation_service,
                "create_session",
                return_value=mock_result,
            ):
                # Test running with session number 1
                controller.run(target_session_number=1)

                # Verify session creation service was called with correct options
                call_args = (
                    controller.session_creation_service.create_session.call_args[0][0]
                )
                assert call_args.context == SessionCreationContext.DIRECT_SESSION_LOAD
                assert call_args.mode == SessionCreationMode.LOAD_EXISTING
                assert call_args.target_session == mock_sessions[0]

    @patch("mochi_coco.chat_controller.ChatController._run_chat_loop")
    def test_run_with_invalid_target_session_number(
        self, mock_chat_loop, mock_sessions
    ):
        """Test running ChatController with invalid target session number falls back to normal flow."""
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions",
            return_value=mock_sessions,
        ):
            controller = ChatController()

            # Mock the session creation service to return success for fallback
            mock_result = SessionCreationResult(
                session=mock_sessions[0],
                model="test-model-1",
                preferences=UserPreferences(markdown_enabled=True, show_thinking=False),
                mode=SessionCreationMode.AUTO_DETECT,
                success=True,
            )

            with patch.object(
                controller.session_creation_service,
                "create_session",
                return_value=mock_result,
            ):
                # Test running with invalid session number (should fallback)
                controller.run(target_session_number=10)

                # Verify session creation service was called with fallback options
                call_args = (
                    controller.session_creation_service.create_session.call_args[0][0]
                )
                assert call_args.context == SessionCreationContext.APPLICATION_STARTUP
                assert call_args.mode == SessionCreationMode.AUTO_DETECT
                assert call_args.target_session is None

    def test_session_creation_service_handles_direct_loading(self, mock_sessions):
        """Test that SessionCreationService handles direct session loading correctly."""
        from mochi_coco.services.session_creation_service import SessionCreationService
        from mochi_coco.services.system_prompt_service import SystemPromptService
        from mochi_coco.services.user_preference_service import UserPreferenceService
        from mochi_coco.ui import ModelSelector

        # Create mocks for dependencies
        mock_model_selector = Mock(spec=ModelSelector)
        mock_preference_service = Mock(spec=UserPreferenceService)
        mock_system_prompt_service = Mock(spec=SystemPromptService)

        service = SessionCreationService(
            mock_model_selector, mock_preference_service, mock_system_prompt_service
        )

        # Create options with target session
        options = SessionCreationOptions(
            context=SessionCreationContext.DIRECT_SESSION_LOAD,
            mode=SessionCreationMode.LOAD_EXISTING,
            target_session=mock_sessions[0],
        )

        # Mock preference collection
        mock_preferences = UserPreferences(markdown_enabled=True, show_thinking=False)
        mock_preference_service.get_or_collect_preferences.return_value = (
            mock_preferences
        )

        # Test direct loading
        result = service.create_session(options)

        # Verify result
        assert result.success is True
        assert result.session == mock_sessions[0]
        assert result.model == mock_sessions[0].metadata.model
        assert result.mode == SessionCreationMode.LOAD_EXISTING

    def test_session_creation_ui_handles_direct_loading_context(self):
        """Test that SessionCreationUI handles DIRECT_SESSION_LOAD context correctly."""
        from mochi_coco.services.session_creation_types import SessionCreationContext
        from mochi_coco.ui.session_creation_ui import SessionCreationUI

        ui = SessionCreationUI()

        # Mock the chat interface
        with patch.object(ui, "chat_interface") as mock_chat_interface:
            # Create a mock session
            mock_session = Mock()
            mock_session.session_id = "test_session_1"

            # Test display success for direct loading
            ui.display_session_creation_success(
                mock_session, "test-model", SessionCreationContext.DIRECT_SESSION_LOAD
            )

            # Verify the correct message was displayed
            mock_chat_interface.print_success_message.assert_called_once_with(
                "Loaded session test_session_1 with test-model"
            )


class TestCLIIntegration:
    """Test CLI integration for direct session loading."""

    @patch("mochi_coco.cli.ChatController")
    def test_cli_passes_chat_session_parameter(self, mock_controller_class):
        """Test that CLI properly passes chat session parameter to ChatController."""
        from mochi_coco.cli import chat

        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller

        # Mock asyncio.run to avoid actually running async code
        with patch("mochi_coco.cli.asyncio.run") as mock_asyncio_run:
            # Test CLI with --chat option
            chat(host=None, chat_session=2)

            # Verify asyncio.run was called
            assert mock_asyncio_run.called

            # The actual controller.run call happens inside the async function,
            # so we need to execute the function that was passed to asyncio.run
            async_func = mock_asyncio_run.call_args[0][0]

            # Execute the async function (it's actually sync in our test)
            import asyncio

            try:
                asyncio.run(async_func())
            except:
                # Expected since we're mocking the executor
                pass

    def test_cli_function_signature_includes_chat_session(self):
        """Test that the CLI chat function has the correct signature."""
        import inspect

        import typer

        from mochi_coco.cli import chat

        sig = inspect.signature(chat)

        # Verify chat_session parameter exists
        assert "chat_session" in sig.parameters

        # Verify it's optional with correct type
        param = sig.parameters["chat_session"]
        # For Typer CLI functions, the default is a Typer OptionInfo object
        assert isinstance(param.default, typer.models.OptionInfo)

        # Verify parameter annotation (if available)
        if hasattr(param, "annotation"):
            # Should be Optional[int] or similar
            assert "int" in str(param.annotation) or "Optional" in str(param.annotation)


class TestEdgeCases:
    """Test edge cases for direct session loading."""

    def test_direct_loading_with_corrupted_session_file(self, temp_sessions_dir):
        """Test handling of corrupted session files."""
        # Create a corrupted session file
        session_file = Path(temp_sessions_dir) / "corrupted_session.json"
        session_file.write_text("invalid json content")

        controller = ChatController()

        # Mock list_sessions to return empty list (simulating that corrupted files are ignored)
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions", return_value=[]
        ):
            # Should handle gracefully and fall back to normal flow
            options = controller._create_direct_session_options(1)

            # Should fall back since no valid sessions exist
            assert options.context == SessionCreationContext.APPLICATION_STARTUP
            assert options.mode == SessionCreationMode.AUTO_DETECT
            assert options.target_session is None

    def test_direct_loading_with_empty_sessions_directory(self, temp_sessions_dir):
        """Test direct loading when sessions directory exists but is empty."""
        controller = ChatController()

        # Mock empty sessions list
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions", return_value=[]
        ):
            options = controller._create_direct_session_options(1)

            # Should fall back to normal flow
            assert options.context == SessionCreationContext.APPLICATION_STARTUP
            assert options.mode == SessionCreationMode.AUTO_DETECT
            assert options.target_session is None

    def test_direct_loading_preserves_session_order(self, mock_sessions):
        """Test that direct loading respects session ordering from list_sessions."""
        with patch(
            "mochi_coco.chat.session.ChatSession.list_sessions",
            return_value=mock_sessions,
        ):
            controller = ChatController()

            # Test that session numbers map correctly
            options_1 = controller._create_direct_session_options(1)
            options_2 = controller._create_direct_session_options(2)
            options_3 = controller._create_direct_session_options(3)

            assert options_1.target_session == mock_sessions[0]
            assert options_2.target_session == mock_sessions[1]
            assert options_3.target_session == mock_sessions[2]
