"""
Simple focused test for the system prompt command fix.

This test verifies that the original issue (/system command crashing due to
method signature mismatch) has been fixed.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from mochi_coco.commands.command_processor import CommandProcessor, CommandResult
from mochi_coco.services.system_prompt_service import SystemPromptService
from mochi_coco.ui.system_prompt_menu_handler import SystemPromptMenuHandler
from mochi_coco.chat.session import ChatSession


class TestSystemPromptCommandFix:
    """Test that the system prompt command fix works correctly."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create temporary sessions directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def temp_system_prompts_dir(self):
        """Create temporary system prompts directory with sample files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            prompts_dir = base_path / "system_prompts"
            prompts_dir.mkdir()

            # Create a sample prompt file
            (prompts_dir / "test_prompt.txt").write_text("You are a test assistant.")

            yield base_path

    @pytest.fixture
    def chat_session(self, temp_sessions_dir):
        """Create a test chat session."""
        return ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

    @pytest.fixture
    def command_processor(self, temp_system_prompts_dir):
        """Create a command processor with mocked dependencies."""
        mock_model_selector = Mock()
        mock_renderer_manager = Mock()

        processor = CommandProcessor(mock_model_selector, mock_renderer_manager)

        # Set up system prompt services
        system_prompt_service = SystemPromptService(base_dir=temp_system_prompts_dir)
        processor.system_prompt_service = system_prompt_service
        processor.system_prompt_menu_handler = SystemPromptMenuHandler(
            system_prompt_service
        )

        return processor

    def test_system_command_does_not_crash(self, command_processor, chat_session):
        """
        Core regression test: /system command should not crash.

        This test verifies that the original TypeError is fixed:
        'CommandProcessor._handle_system_prompt_command() takes 2 positional
        arguments but 3 were given'
        """
        # Mock the menu handler to avoid UI interactions
        with patch.object(
            command_processor.system_prompt_menu_handler,
            "select_system_prompt",
            return_value=None,
        ):
            try:
                # This should NOT raise a TypeError
                result = command_processor.process_command(
                    "/system", chat_session, "test-model"
                )

                # Verify we got a valid result
                assert isinstance(result, CommandResult)
                assert result.should_continue is True

            except TypeError as e:
                if "takes 2 positional arguments but 3 were given" in str(e):
                    pytest.fail(f"Original bug has regressed: {e}")
                else:
                    # Re-raise if it's a different TypeError
                    raise

    def test_system_command_method_signature(self, command_processor):
        """Test that the method signature accepts both session and args parameters."""
        import inspect

        # Get the method signature
        method = command_processor._handle_system_prompt_command
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        # Should have 'session' and 'args' parameters (excluding 'self')
        assert "session" in params, "Method should accept 'session' parameter"
        assert "args" in params, "Method should accept 'args' parameter"

        # Verify args has a default value
        args_param = sig.parameters["args"]
        assert args_param.default == "", (
            "args parameter should have empty string default"
        )

    def test_system_command_called_with_args(self, command_processor, chat_session):
        """Test that the method can be called directly with args parameter."""
        with patch.object(
            command_processor.system_prompt_service,
            "has_system_prompts",
            return_value=False,
        ):
            # This should work without raising TypeError
            result = command_processor._handle_system_prompt_command(
                chat_session, "test_args"
            )
            assert isinstance(result, CommandResult)

    def test_dynamic_command_mapping_includes_system(
        self, command_processor, chat_session
    ):
        """Test that /system is properly included in dynamic command mapping."""
        command_map = command_processor._build_dynamic_command_map(chat_session)

        # /system should be in the command map
        assert "/system" in command_map, (
            "/system command should be in dynamic command map"
        )
        assert command_map["/system"] == "_handle_system_prompt_command"

    def test_process_command_calls_handler_correctly(
        self, command_processor, chat_session
    ):
        """Test that process_command calls the handler with correct arguments."""
        with patch.object(
            command_processor,
            "_handle_system_prompt_command",
            return_value=CommandResult(),
        ) as mock_handler:
            # Process the command
            result = command_processor.process_command(
                "/system", chat_session, "test-model"
            )

            # Verify the handler was called with session and empty args
            mock_handler.assert_called_once_with(chat_session, "")
            assert isinstance(result, CommandResult)

    def test_process_command_with_arguments(self, command_processor, chat_session):
        """Test that process_command passes arguments to the handler."""
        with patch.object(
            command_processor,
            "_handle_system_prompt_command",
            return_value=CommandResult(),
        ) as mock_handler:
            # Process command with arguments
            _result = command_processor.process_command(
                "/system reload", chat_session, "test-model"
            )

            # Verify the handler was called with session and arguments
            mock_handler.assert_called_once_with(chat_session, "reload")

    @patch("typer.secho")
    def test_unknown_commands_still_work(
        self, mock_secho, command_processor, chat_session
    ):
        """Regression test: ensure unknown commands still produce error messages."""
        result = command_processor.process_command(
            "/unknown", chat_session, "test-model"
        )

        # Should produce "Unknown command" message
        error_calls = [
            call for call in mock_secho.call_args_list if "Unknown command" in str(call)
        ]
        assert len(error_calls) > 0, "Unknown command should produce error message"
        assert result.should_continue is False

    def test_system_vs_unknown_command_behavior(self, command_processor, chat_session):
        """Test that /system behaves differently from truly unknown commands."""
        # Test unknown command
        with patch("typer.secho") as mock_secho_unknown:
            result_unknown = command_processor.process_command(
                "/fakecmd", chat_session, "test-model"
            )

            unknown_calls = [
                call
                for call in mock_secho_unknown.call_args_list
                if "Unknown command" in str(call)
            ]
            assert len(unknown_calls) > 0, "Unknown command should show error"
            assert result_unknown.should_continue is False

        # Test /system command
        with patch("typer.secho") as mock_secho_system:
            with patch.object(
                command_processor.system_prompt_service,
                "has_system_prompts",
                return_value=False,
            ):
                result_system = command_processor.process_command(
                    "/system", chat_session, "test-model"
                )

                # Should NOT show "Unknown command" message
                unknown_calls = [
                    call
                    for call in mock_secho_system.call_args_list
                    if "Unknown command" in str(call)
                ]
                assert len(unknown_calls) == 0, (
                    "/system should not show 'Unknown command' error"
                )
                assert result_system.should_continue is True
