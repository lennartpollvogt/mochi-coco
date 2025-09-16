"""
Integration tests for command processing workflows.

Tests the complete command flow including command parsing, state changes,
UI updates, and integration between CommandProcessor, SessionManager,
and other components.
"""

import pytest
import tempfile
from unittest.mock import Mock, patch

from mochi_coco.commands.command_processor import CommandProcessor, CommandResult
from mochi_coco.chat.session import ChatSession
from mochi_coco.services import RendererManager
from mochi_coco.ui import ModelSelector
from mochi_coco.rendering import RenderingMode


@pytest.mark.integration
class TestCommandProcessingFlow:
    """Integration tests for command processing workflows."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create temporary directory for session files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_model_selector(self):
        """Create mock ModelSelector for command testing."""
        mock_selector = Mock(spec=ModelSelector)
        mock_selector.client = Mock()
        mock_selector.renderer = Mock()
        mock_selector.menu_display = Mock()
        mock_selector.display_chat_history = Mock()
        return mock_selector

    @pytest.fixture
    def mock_renderer_manager(self):
        """Create mock RendererManager for testing."""
        mock_manager = Mock(spec=RendererManager)
        mock_manager.renderer = Mock()
        mock_manager.is_markdown_enabled.return_value = True
        mock_manager.is_thinking_enabled.return_value = False
        mock_manager.toggle_markdown_mode.return_value = RenderingMode.PLAIN
        mock_manager.toggle_thinking_display.return_value = True
        mock_manager.can_toggle_thinking.return_value = True
        return mock_manager

    @pytest.fixture
    def command_processor(self, mock_model_selector, mock_renderer_manager):
        """Create CommandProcessor with mock dependencies."""
        return CommandProcessor(mock_model_selector, mock_renderer_manager)

    @pytest.fixture
    def sample_session(self, temp_sessions_dir):
        """Create a sample session with messages for testing."""
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        session.add_user_message("Hello, how are you?")

        # Add mock assistant response
        mock_response = Mock()
        mock_response.message = Mock()
        mock_response.message.__getitem__ = lambda self, key: "I'm doing well, thank you!"
        mock_response.message.role = "assistant"
        mock_response.model = "test-model"
        mock_response.eval_count = 90
        mock_response.prompt_eval_count = 45
        session.add_message(mock_response)

        session.add_user_message("What's the weather like?")
        session.save_session()
        return session

    def test_exit_command_processing_flow(self, command_processor, sample_session):
        """
        Test complete flow for exit commands.

        Tests integration of:
        - Command parsing and recognition
        - Exit command variants
        - Proper result generation
        """
        exit_commands = ["/exit", "/quit", "/q", "/EXIT", "/Quit"]

        for command in exit_commands:
            result = command_processor.process_command(command, sample_session, "test-model")

            assert isinstance(result, CommandResult)
            assert result.should_exit is True
            assert result.should_continue is False
            assert result.new_session is None
            assert result.new_model is None

    def test_menu_command_integration_flow(
        self,
        command_processor,
        sample_session,
        mock_model_selector,
        mock_renderer_manager
    ):
        """
        Test complete menu command workflow with user interactions.

        Tests integration of:
        - Menu command processing
        - UI menu display
        - User selection handling
        - Sub-command execution
        """
        # Mock menu display and user interaction
        mock_model_selector.menu_display.display_command_menu = Mock()

        # Mock user choosing option 3 (markdown toggle) then quit
        with patch('mochi_coco.ui.user_interaction.UserInteraction') as MockUserInteraction:
            mock_interaction = Mock()
            mock_interaction.get_user_input.side_effect = ["3", "q"]  # Toggle markdown, then quit
            MockUserInteraction.return_value = mock_interaction

            # Mock re-render function
            with patch('mochi_coco.commands.command_processor.re_render_chat_history') as mock_rerender:
                result = command_processor.process_command("/menu", sample_session, "test-model")

                # Verify menu was displayed
                mock_model_selector.menu_display.display_command_menu.assert_called()

                # Verify markdown toggle was called
                mock_renderer_manager.toggle_markdown_mode.assert_called_once()

                # Verify re-render was called
                mock_rerender.assert_called_once_with(sample_session, mock_model_selector)

                # Verify result
                assert isinstance(result, CommandResult)
                assert result.should_continue is True
                assert result.should_exit is False

    def test_edit_command_complete_workflow(
        self,
        command_processor,
        sample_session,
        mock_model_selector,
        mock_renderer_manager
    ):
        """
        Test complete message editing workflow.

        Tests integration of:
        - Edit command processing
        - User message selection
        - Message editing with truncation
        - LLM response generation
        - Session persistence
        """

        # Mock edit menu display
        mock_model_selector.menu_display.display_edit_messages_table = Mock()

        # Mock user selecting message #1 and providing edited content
        with patch('mochi_coco.ui.user_interaction.UserInteraction') as MockUserInteraction:
            mock_interaction = Mock()
            mock_interaction.get_edit_selection.return_value = 1  # Select first user message
            MockUserInteraction.return_value = mock_interaction

            # Mock user input for edited message
            with patch('mochi_coco.user_prompt.get_user_input_with_prefill') as mock_input:
                mock_input.return_value = "Hello, how are you doing today?"  # Edited message

                # Mock LLM response for continued conversation
                #mock_streaming_response = Mock()
                mock_final_chunk = Mock()
                mock_final_chunk.message = Mock()
                mock_final_chunk.message.__getitem__ = lambda self, key: "I'm doing great, thanks for asking!"
                mock_final_chunk.message.role = "assistant"
                mock_final_chunk.model = "test-model"
                mock_final_chunk.eval_count = 85
                mock_final_chunk.prompt_eval_count = 42

                mock_model_selector.client.chat_stream.return_value = iter([mock_final_chunk])
                mock_renderer_manager.renderer.render_streaming_response.return_value = mock_final_chunk

                # Mock re-render function - patch where it's locally imported in _handle_edit_command
                with patch('mochi_coco.utils.re_render_chat_history') as mock_rerender:
                    result = command_processor.process_command("/edit", sample_session, "test-model")

                    # Verify edit selection UI was shown
                    mock_model_selector.menu_display.display_edit_messages_table.assert_called_once_with(sample_session)

                    # Verify user was prompted for edit selection
                    mock_interaction.get_edit_selection.assert_called_once()

                    # Verify user was prompted for edited content
                    mock_input.assert_called_once()

                    # Verify re-render was called
                    mock_rerender.assert_called_once()

                    # Verify LLM was called for continuation
                    mock_model_selector.client.chat_stream.assert_called_once()

                    # Verify session was modified
                    # Message should be edited and conversation continued
                    assert len(sample_session.messages) >= 2  # At least edited message + new response
                    assert sample_session.messages[0].content == "Hello, how are you doing today?"

                    # Verify result
                    assert isinstance(result, CommandResult)
                    assert result.should_continue is True

    def test_edit_command_with_no_user_messages(self, command_processor, temp_sessions_dir):
        """
        Test edit command when session has no user messages.

        Tests integration of:
        - Edge case handling
        - Proper error messaging
        - Graceful fallback
        """
        # Create session with only assistant messages
        empty_session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)

        mock_response = Mock()
        mock_response.message = Mock()
        mock_response.message.__getitem__ = lambda self, key: "Hello there!"
        mock_response.message.role = "assistant"
        mock_response.model = "test-model"
        mock_response.eval_count = 50
        mock_response.prompt_eval_count = 25
        empty_session.add_message(mock_response)

        with patch('typer.secho') as mock_secho:
            result = command_processor.process_command("/edit", empty_session, "test-model")

            # Verify appropriate warning was shown
            warning_calls = [call for call in mock_secho.call_args_list
                           if "No user messages to edit" in str(call)]
            assert len(warning_calls) > 0

            # Verify graceful handling
            assert isinstance(result, CommandResult)
            assert result.should_continue is True

    def test_edit_command_user_cancellation_flow(
        self,
        command_processor,
        sample_session,
        mock_model_selector
    ):
        """
        Test edit command when user cancels at different stages.

        Tests integration of:
        - User cancellation handling
        - Multiple cancellation points
        - State preservation
        """
        original_messages = len(sample_session.messages)

        # Mock edit selection menu
        mock_model_selector.menu_display.display_edit_messages_table = Mock()

        # Test cancellation during selection
        with patch('mochi_coco.ui.user_interaction.UserInteraction') as MockUserInteraction:
            mock_interaction = Mock()
            mock_interaction.get_edit_selection.return_value = None  # User cancelled
            MockUserInteraction.return_value = mock_interaction

            with patch('typer.secho') as mock_secho:
                result = command_processor.process_command("/edit", sample_session, "test-model")

                # Verify cancellation message
                cancel_calls = [call for call in mock_secho.call_args_list
                              if "cancelled" in str(call).lower()]
                assert len(cancel_calls) > 0

                # Verify session unchanged
                assert len(sample_session.messages) == original_messages

                # Verify result
                assert isinstance(result, CommandResult)
                assert result.should_continue is True

    def test_model_switching_command_integration(
        self,
        command_processor,
        sample_session,
        mock_model_selector
    ):
        """
        Test model switching through menu command.

        Tests integration of:
        - Menu navigation to model selection
        - Model switching logic
        - Session update with new model
        - Persistence of model change
        """
        # Mock user choosing option 2 (models) in menu, then selecting new model
        with patch('mochi_coco.ui.user_interaction.UserInteraction') as MockUserInteraction:
            mock_interaction = Mock()
            mock_interaction.get_user_input.side_effect = ["2", "q"]  # Select models, then quit
            MockUserInteraction.return_value = mock_interaction

            # Mock model selection
            mock_model_selector.select_model.return_value = "new-model"

            result = command_processor.process_command("/menu", sample_session, "test-model")

            # Verify model selection was called
            mock_model_selector.select_model.assert_called_once()

            # Verify session model was updated
            assert sample_session.model == "new-model"
            assert sample_session.metadata.model == "new-model"

            # Verify result contains new model
            assert result.new_model == "new-model"

    def test_session_switching_command_integration(
        self,
        command_processor,
        sample_session,
        mock_model_selector,
        mock_renderer_manager,
        temp_sessions_dir
    ):
        """
        Test session switching through menu command.

        Tests integration of:
        - Menu navigation to session selection
        - Session switching logic
        - Renderer configuration updates
        - State transition between sessions
        """
        # Create another session to switch to
        other_session = ChatSession(model="other-model", sessions_dir=temp_sessions_dir)
        other_session.add_user_message("Different conversation")
        other_session.save_session()

        # Mock the session creation service to avoid input handling issues
        with patch('mochi_coco.services.session_creation_service.SessionCreationService.create_session') as mock_create:
            from mochi_coco.services.session_creation_types import SessionCreationResult, UserPreferences, SessionCreationMode

            preferences = UserPreferences(markdown_enabled=False, show_thinking=True)
            mock_create.return_value = SessionCreationResult(
                session=other_session,
                model="other-model",
                preferences=preferences,
                mode=SessionCreationMode.LOAD_EXISTING,
                success=True,
                error_message=None
            )

            # Mock user interaction to avoid actual input
            with patch('mochi_coco.ui.user_interaction.get_user_input_single_line', return_value="1"):
                result = command_processor.process_command("/menu", sample_session, "test-model")

                # Verify session creation was called (indicating menu navigation worked)
                mock_create.assert_called_once()

                # Verify renderer was reconfigured
                mock_renderer_manager.configure_renderer.assert_called_once_with(False, True)

                # Verify result contains new session and model
                assert result.new_session == other_session
                assert result.new_model == "other-model"

    def test_markdown_toggle_command_integration(
        self,
        command_processor,
        sample_session,
        mock_model_selector,
        mock_renderer_manager
    ):
        """
        Test markdown rendering toggle through menu.

        Tests integration of:
        - Markdown mode toggling
        - Chat history re-rendering
        - UI feedback
        - State persistence across toggle
        """
        # Mock renderer returning new mode
        mock_renderer_manager.toggle_markdown_mode.return_value = RenderingMode.MARKDOWN

        # Mock user choosing option 3 (markdown) in menu
        with patch('mochi_coco.ui.user_interaction.UserInteraction') as MockUserInteraction:
            mock_interaction = Mock()
            mock_interaction.get_user_input.side_effect = ["3", "q"]  # Toggle markdown, then quit
            MockUserInteraction.return_value = mock_interaction

            # Mock re-render function
            with patch('mochi_coco.commands.command_processor.re_render_chat_history') as mock_rerender:
                with patch('typer.secho') as mock_secho:
                    result = command_processor.process_command("/menu", sample_session, "test-model")

                    # Verify markdown toggle was called
                    mock_renderer_manager.toggle_markdown_mode.assert_called_once()

                    # Verify re-render was called
                    mock_rerender.assert_called_once_with(sample_session, mock_model_selector)

                    # Verify success message was shown
                    success_calls = [call for call in mock_secho.call_args_list
                                   if "enabled" in str(call)]
                    assert len(success_calls) > 0

                    # Verify result
                    assert isinstance(result, CommandResult)
                    assert result.should_continue is True

    def test_thinking_toggle_command_integration(
        self,
        command_processor,
        sample_session,
        mock_model_selector,
        mock_renderer_manager
    ):
        """
        Test thinking blocks toggle through menu.

        Tests integration of:
        - Thinking display toggling
        - Conditional availability based on markdown mode
        - Chat history re-rendering with thinking blocks
        """
        # Test successful thinking toggle
        mock_renderer_manager.can_toggle_thinking.return_value = True
        mock_renderer_manager.toggle_thinking_display.return_value = True

        with patch('mochi_coco.ui.user_interaction.UserInteraction') as MockUserInteraction:
            mock_interaction = Mock()
            mock_interaction.get_user_input.side_effect = ["4", "q"]  # Toggle thinking, then quit
            MockUserInteraction.return_value = mock_interaction

            with patch('mochi_coco.commands.command_processor.re_render_chat_history') as mock_rerender:
                with patch('typer.secho') as mock_secho:
                    # Actually call the menu command to trigger the thinking toggle
                    command_processor.process_command("/menu", sample_session, "test-model")

                    # Verify thinking toggle was attempted
                    mock_renderer_manager.can_toggle_thinking.assert_called_once()
                    mock_renderer_manager.toggle_thinking_display.assert_called_once()

                    # Verify re-render was called
                    mock_rerender.assert_called_once_with(sample_session, mock_model_selector)

                    # Verify success message
                    success_calls = [call for call in mock_secho.call_args_list
                                   if "shown" in str(call)]
                    assert len(success_calls) > 0

    def test_thinking_toggle_when_not_available(
        self,
        command_processor,
        sample_session,
        mock_renderer_manager
    ):
        """
        Test thinking toggle when not in markdown mode.

        Tests integration of:
        - Conditional command availability
        - User feedback for unavailable features
        - Graceful handling of invalid operations
        """
        # Mock thinking toggle not available
        mock_renderer_manager.can_toggle_thinking.return_value = False

        with patch('mochi_coco.ui.user_interaction.UserInteraction') as MockUserInteraction:
            mock_interaction = Mock()
            mock_interaction.get_user_input.side_effect = ["4", "q"]  # Try thinking toggle, then quit
            MockUserInteraction.return_value = mock_interaction

            with patch('typer.secho') as mock_secho:
                command_processor.process_command("/menu", sample_session, "test-model")

                # Verify warning message was shown
                warning_calls = [call for call in mock_secho.call_args_list
                               if "markdown mode" in str(call)]
                assert len(warning_calls) > 0

                # Verify toggle was not attempted
                mock_renderer_manager.toggle_thinking_display.assert_not_called()

    def test_unrecognized_command_handling(self, command_processor, sample_session):
        """
        Test handling of unrecognized commands.

        Tests integration of:
        - Unknown command detection
        - Proper fallback behavior
        - No unintended side effects
        """
        unrecognized_commands = [
            "/unknown",
            "/help",
            "/status",
            "/random",
            "not_a_command"
        ]

        for command in unrecognized_commands:
            result = command_processor.process_command(command, sample_session, "test-model")

            # Should return result indicating no action taken
            assert isinstance(result, CommandResult)
            assert result.should_continue is False  # Not a recognized command
            assert result.should_exit is False
            assert result.new_session is None
            assert result.new_model is None

    def test_command_error_handling_and_recovery(
        self,
        command_processor,
        sample_session,
        mock_model_selector,
        mock_renderer_manager
    ):
        """
        Test error handling during command processing.

        Tests integration of:
        - Error propagation and handling
        - Graceful degradation
        - User feedback during errors
        - State preservation during failures
        """
        # Mock model selector raising an exception
        mock_model_selector.select_model.side_effect = Exception("Model selection failed")

        with patch('mochi_coco.ui.user_interaction.UserInteraction') as MockUserInteraction:
            mock_interaction = Mock()
            mock_interaction.get_user_input.side_effect = ["2", "q"]  # Try models, then quit
            MockUserInteraction.return_value = mock_interaction

            # Should not raise exception, should handle gracefully
            result = command_processor.process_command("/menu", sample_session, "test-model")

            # Verify result is still valid (command processor should handle errors)
            assert isinstance(result, CommandResult)
            # Session should remain unchanged
            assert sample_session.model == "test-model"

    def test_command_result_state_management(self, command_processor, sample_session):
        """
        Test proper CommandResult state management across different commands.

        Tests integration of:
        - CommandResult creation and properties
        - State transition signaling
        - Proper result propagation
        """
        # Test various command results
        test_cases = [
            ("/exit", {"should_exit": True, "should_continue": False}),
            ("/quit", {"should_exit": True, "should_continue": False}),
            ("/unknown", {"should_exit": False, "should_continue": False}),
        ]

        for command, expected_state in test_cases:
            result = command_processor.process_command(command, sample_session, "test-model")

            assert isinstance(result, CommandResult)
            for attr, expected_value in expected_state.items():
                actual_value = getattr(result, attr)
                assert actual_value == expected_value, f"Command {command}: {attr} should be {expected_value}, got {actual_value}"
