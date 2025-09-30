"""
Comprehensive tests for system prompt command functionality.

Tests cover the /system command processing, system prompt service,
menu handler interactions, and error handling scenarios.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from mochi_coco.commands.command_processor import CommandProcessor, CommandResult
from mochi_coco.services.system_prompt_service import SystemPromptService
from mochi_coco.ui.system_prompt_menu_handler import (
    SystemPromptMenuHandler,
    SystemPromptSelectionContext,
)
from mochi_coco.chat.session import ChatSession


@pytest.fixture
def temp_system_prompts_dir():
    """Create a temporary directory with sample system prompt files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create system_prompts subdirectory
        prompts_dir = temp_path / "system_prompts"
        prompts_dir.mkdir()

        # Create sample prompt files
        (prompts_dir / "coding_assistant.txt").write_text(
            "You are an expert software engineer. Help with coding tasks."
        )
        (prompts_dir / "creative_writer.md").write_text(
            "# Creative Writing Assistant\n\nYou are a creative writing assistant."
        )

        yield temp_path


@pytest.fixture
def empty_system_prompts_dir():
    """Create a temporary directory with no system prompt files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create empty system_prompts subdirectory
        prompts_dir = temp_path / "system_prompts"
        prompts_dir.mkdir()
        yield temp_path


@pytest.fixture
def mock_model_selector():
    """Create a mock ModelSelector."""
    return Mock()


@pytest.fixture
def mock_renderer_manager():
    """Create a mock RendererManager."""
    return Mock()


@pytest.fixture
def sample_chat_session(temp_sessions_dir):
    """Create a sample chat session for testing."""
    session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
    session.add_user_message("Hello, how are you?")
    return session


@pytest.fixture
def system_prompt_service(temp_system_prompts_dir):
    """Create a SystemPromptService with sample prompts."""
    return SystemPromptService(base_dir=temp_system_prompts_dir)


@pytest.fixture
def empty_system_prompt_service(empty_system_prompts_dir):
    """Create a SystemPromptService with no prompts."""
    return SystemPromptService(base_dir=empty_system_prompts_dir)


@pytest.fixture
def command_processor(
    mock_model_selector, mock_renderer_manager, system_prompt_service
):
    """Create a CommandProcessor with mocked dependencies."""
    processor = CommandProcessor(mock_model_selector, mock_renderer_manager)
    processor.system_prompt_service = system_prompt_service
    processor.system_prompt_menu_handler = SystemPromptMenuHandler(
        system_prompt_service
    )
    return processor


@pytest.fixture
def empty_command_processor(
    mock_model_selector, mock_renderer_manager, empty_system_prompt_service
):
    """Create a CommandProcessor with no system prompts available."""
    processor = CommandProcessor(mock_model_selector, mock_renderer_manager)
    processor.system_prompt_service = empty_system_prompt_service
    processor.system_prompt_menu_handler = SystemPromptMenuHandler(
        empty_system_prompt_service
    )
    return processor


class TestSystemPromptCommandProcessing:
    """Test system prompt command processing in CommandProcessor."""

    def test_system_command_signature_accepts_args(
        self, command_processor, sample_chat_session
    ):
        """Test that _handle_system_prompt_command accepts args parameter."""
        # This test ensures the method signature fix is working
        with patch.object(
            command_processor.system_prompt_menu_handler,
            "select_system_prompt",
            return_value=None,
        ):
            result = command_processor._handle_system_prompt_command(
                sample_chat_session, ""
            )
            assert isinstance(result, CommandResult)

    def test_system_command_in_dynamic_mapping(
        self, command_processor, sample_chat_session
    ):
        """Test that /system command is properly mapped in dynamic command map."""
        command_map = command_processor._build_dynamic_command_map(sample_chat_session)
        assert "/system" in command_map
        assert command_map["/system"] == "_handle_system_prompt_command"

    def test_process_system_command_calls_handler(
        self, command_processor, sample_chat_session
    ):
        """Test that process_command properly calls the system prompt handler."""
        with patch.object(
            command_processor,
            "_handle_system_prompt_command",
            return_value=CommandResult(),
        ) as mock_handler:
            result = command_processor.process_command(
                "/system", sample_chat_session, "test-model"
            )
            mock_handler.assert_called_once_with(sample_chat_session, "")
            assert isinstance(result, CommandResult)


class TestSystemPromptSelection:
    """Test system prompt selection functionality."""

    def test_system_command_with_available_prompts(
        self, command_processor, sample_chat_session
    ):
        """Test /system command behavior when system prompts are available."""
        mock_content = "You are a helpful assistant."

        with patch.object(
            command_processor.system_prompt_menu_handler,
            "select_system_prompt",
            return_value=mock_content,
        ):
            with patch.object(
                sample_chat_session, "update_system_message"
            ) as mock_update:
                with patch("typer.secho"):
                    result = command_processor._handle_system_prompt_command(
                        sample_chat_session, ""
                    )

                    mock_update.assert_called_once_with(mock_content)
                    assert isinstance(result, CommandResult)

    def test_system_command_selection_cancelled(
        self, command_processor, sample_chat_session
    ):
        """Test /system command when user cancels selection."""
        with patch.object(
            command_processor.system_prompt_menu_handler,
            "select_system_prompt",
            return_value=None,
        ):
            result = command_processor._handle_system_prompt_command(
                sample_chat_session, ""
            )

            assert isinstance(result, CommandResult)


class TestSystemPromptCommandErrors:
    """Test error handling in system prompt commands."""

    def test_system_command_no_prompts_available(
        self, empty_command_processor, sample_chat_session
    ):
        """Test /system command behavior when no system prompts are available."""
        with patch("typer.secho"):
            result = empty_command_processor._handle_system_prompt_command(
                sample_chat_session, ""
            )

            assert isinstance(result, CommandResult)

    def test_system_command_exception_handling(
        self, command_processor, sample_chat_session
    ):
        """Test /system command handles exceptions gracefully."""
        with patch.object(
            command_processor.system_prompt_service,
            "has_system_prompts",
            side_effect=Exception("Test error"),
        ):
            with patch("typer.secho"):
                result = command_processor._handle_system_prompt_command(
                    sample_chat_session, ""
                )

                assert isinstance(result, CommandResult)


class TestSystemPromptServiceBasics:
    """Test basic SystemPromptService functionality."""

    def test_has_system_prompts_with_prompts(self, system_prompt_service):
        """Test has_system_prompts returns True when prompts exist."""
        assert system_prompt_service.has_system_prompts() is True

    def test_has_system_prompts_empty_dir(self, empty_system_prompt_service):
        """Test has_system_prompts returns False when no prompts exist."""
        assert empty_system_prompt_service.has_system_prompts() is False

    def test_get_system_prompts_dir(self, temp_system_prompts_dir):
        """Test get_system_prompts_dir returns correct path."""
        service = SystemPromptService(base_dir=temp_system_prompts_dir)
        expected_path = temp_system_prompts_dir / "system_prompts"
        assert service.get_system_prompts_dir() == expected_path


class TestSystemPromptCommandIntegration:
    """Test integration between command processing and system prompt functionality."""

    def test_full_system_command_flow(self, command_processor, sample_chat_session):
        """Test complete flow from command input to system prompt update."""
        mock_content = "You are a coding assistant."

        with patch.object(
            command_processor.system_prompt_menu_handler,
            "select_system_prompt",
            return_value=mock_content,
        ) as mock_select:
            with patch.object(
                sample_chat_session, "update_system_message"
            ) as mock_update:
                with patch.object(
                    sample_chat_session,
                    "get_current_system_prompt_file",
                    return_value=None,
                ):
                    with patch("typer.secho"):
                        # Process the command
                        result = command_processor.process_command(
                            "/system", sample_chat_session, "test-model"
                        )

                        # Verify the flow
                        mock_select.assert_called_once_with(
                            SystemPromptSelectionContext.FROM_MENU
                        )
                        mock_update.assert_called_once_with(mock_content)
                        assert isinstance(result, CommandResult)
                        assert result.should_continue is True

    def test_system_command_case_insensitive(
        self, command_processor, sample_chat_session
    ):
        """Test that /SYSTEM command works (case insensitive)."""
        with patch.object(
            command_processor,
            "_handle_system_prompt_command",
            return_value=CommandResult(),
        ) as mock_handler:
            _result = command_processor.process_command(
                "/SYSTEM", sample_chat_session, "test-model"
            )
            mock_handler.assert_called_once_with(sample_chat_session, "")


class TestSystemPromptCommandRegression:
    """Regression tests to prevent the original issue from reoccurring."""

    def test_system_command_does_not_crash_with_args(
        self, command_processor, sample_chat_session
    ):
        """Regression test: /system command should not crash when called with args."""
        # This is the core regression test for the original bug
        try:
            with patch.object(
                command_processor.system_prompt_menu_handler,
                "select_system_prompt",
                return_value=None,
            ):
                result = command_processor.process_command(
                    "/system", sample_chat_session, "test-model"
                )
                # If we get here without exception, the bug is fixed
                assert isinstance(result, CommandResult)
        except TypeError as e:
            if "takes 2 positional arguments but 3 were given" in str(e):
                pytest.fail("Original bug has regressed: method signature issue")
            else:
                raise

    def test_system_command_method_signature_compatibility(self, command_processor):
        """Test that _handle_system_prompt_command has compatible signature with other dynamic handlers."""
        import inspect

        # Get method signatures
        system_sig = inspect.signature(command_processor._handle_system_prompt_command)
        tools_sig = inspect.signature(command_processor._handle_tools_command)

        # Both should have 'self', 'session', and 'args' parameters
        system_params = list(system_sig.parameters.keys())
        tools_params = list(tools_sig.parameters.keys())

        assert "session" in system_params
        assert "args" in system_params
        assert len(system_params) == len(
            tools_params
        )  # Should have same number of parameters

    def test_unknown_commands_still_work(self, command_processor, sample_chat_session):
        """Test that unknown commands still produce proper error messages."""
        with patch("typer.secho") as mock_secho:
            result = command_processor.process_command(
                "/unknown_command", sample_chat_session, "test-model"
            )

            # Check that some error message was called
            assert mock_secho.called
            assert result.should_continue is False
