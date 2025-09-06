"""
Integration tests for complete chat flow workflows.

Tests the full user journey from chat initialization through message exchange,
covering the integration of ChatController, OllamaClient, ChatSession,
MarkdownRenderer, and persistence layers.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from mochi_coco.chat_controller import ChatController
from mochi_coco.chat.session import ChatSession
from mochi_coco.ollama.client import OllamaClient
from mochi_coco.rendering import MarkdownRenderer, RenderingMode


class MockMessage:
    """Mock message object that supports both property and dictionary access."""
    def __init__(self, content):
        self.content = content
        self.role = "assistant"

    def __getitem__(self, key):
        return getattr(self, key, "")


@pytest.mark.integration
class TestCompleteChatFlow:
    """Integration tests for complete chat workflows."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create temporary directory for session files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_ollama_streaming_response(self):
        """Create realistic streaming response for chat."""
        def create_stream():
            # First content chunk
            chunk1 = Mock()
            chunk1.message = Mock()
            chunk1.message.__getitem__ = lambda self, key: "Hello! I'm here to help you."
            chunk1.message.content = "Hello! I'm here to help you."
            chunk1.message.role = "assistant"
            chunk1.done = False
            chunk1.eval_count = None
            chunk1.prompt_eval_count = None
            yield chunk1

            # Second content chunk
            chunk2 = Mock()
            chunk2.message = Mock()
            chunk2.message.__getitem__ = lambda self, key: " What can I do for you today?"
            chunk2.message.content = " What can I do for you today?"
            chunk2.message.role = "assistant"
            chunk2.done = False
            chunk2.eval_count = None
            chunk2.prompt_eval_count = None
            yield chunk2

            # Final metadata chunk
            final_chunk = Mock()
            final_chunk.message = Mock()
            final_chunk.message.__getitem__ = lambda self, key: "Hello! I'm here to help you. What can I do for you today?"
            final_chunk.message.content = "Hello! I'm here to help you. What can I do for you today?"
            final_chunk.message.role = "assistant"
            final_chunk.done = True
            final_chunk.model = "test-model"
            final_chunk.eval_count = 95
            final_chunk.prompt_eval_count = 45
            yield final_chunk

        return create_stream

    @pytest.fixture
    def mock_ollama_client_integration(self, mock_ollama_streaming_response):
        """Create mock OllamaClient with realistic behavior for integration testing."""
        with patch('mochi_coco.chat_controller.OllamaClient') as MockClientClass:
            mock_client = Mock(spec=OllamaClient)

            # Mock model listing
            mock_model = Mock()
            mock_model.name = "test-model"
            mock_model.size_mb = 1500.0
            mock_model.format = "gguf"
            mock_model.family = "llama"
            mock_model.parameter_size = "7B"
            mock_model.quantization_level = "Q4_0"
            mock_client.list_models.return_value = [mock_model]

            # Mock streaming chat - use side_effect to create new generator for each call
            mock_client.chat_stream.side_effect = lambda *args, **kwargs: mock_ollama_streaming_response()

            MockClientClass.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_model_selector_for_integration(self):
        """Mock ModelSelector to return predetermined choices for integration testing."""
        with patch('mochi_coco.chat_controller.ModelSelector') as MockSelector:
            mock_selector = Mock()

            # Mock session initialization - return new session
            mock_selector.select_session_or_new.return_value = (
                None,  # session (None = new session)
                "test-model",  # selected_model
                True,  # markdown_enabled
                False  # show_thinking
            )

            MockSelector.return_value = mock_selector
            yield mock_selector

    @pytest.fixture
    def mock_user_input_sequence(self):
        """Mock user input sequence for automated testing."""
        inputs = ["Hello, how are you?", "Tell me a joke", "/exit"]
        input_iter = iter(inputs)

        def mock_input():
            try:
                return next(input_iter)
            except StopIteration:
                raise EOFError()  # Simulate user ending input

        with patch('mochi_coco.chat_controller.get_user_input', side_effect=mock_input):
            yield inputs

    def test_complete_new_chat_session_flow(
        self,
        temp_sessions_dir,
        mock_ollama_client_integration,
        mock_model_selector_for_integration,
        mock_user_input_sequence
    ):
        """
        Test complete flow: Initialize new session -> Send message -> Get response -> Save session.

        This tests the integration of:
        - ChatController initialization
        - Session creation and setup
        - Message processing and streaming
        - Session persistence
        """
        controller = ChatController()

        # Mock the renderer to capture output without terminal formatting
        with patch.object(controller.renderer, 'render_streaming_response') as mock_render:
            # Create a final chunk that renderer would return
            final_chunk = Mock()
            final_chunk.message = Mock()
            final_chunk.message.__getitem__ = lambda self, key: "Hello! I'm here to help you. What can I do for you today?"
            final_chunk.message.role = "assistant"
            final_chunk.model = "test-model"
            final_chunk.eval_count = 95
            final_chunk.prompt_eval_count = 45
            mock_render.return_value = final_chunk

            # Run the chat controller (will exit after /exit command)
            controller.run()

        # Verify session was created and persisted
        assert controller.session is not None
        assert controller.session.session_id is not None
        assert controller.selected_model == "test-model"

        # Verify session file was created
        session_files = list(Path(controller.session.sessions_dir).glob("*.json"))
        assert len(session_files) >= 1

        # Verify session contains expected messages
        session = controller.session
        assert len(session.messages) >= 4  # At least 2 user messages + 2 assistant responses

        # Check message sequence
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello, how are you?"
        assert session.messages[1].role == "assistant"
        assert session.messages[2].role == "user"
        assert session.messages[2].content == "Tell me a joke"
        assert session.messages[3].role == "assistant"

        # Verify API calls were made correctly
        assert mock_ollama_client_integration.chat_stream.call_count == 2

        # Verify session metadata
        assert session.metadata.model == "test-model"
        assert session.metadata.message_count == len(session.messages)

    def test_session_loading_and_continuation_flow(
        self,
        temp_sessions_dir,
        mock_ollama_client_integration
    ):
        """
        Test loading existing session and continuing conversation.

        Tests integration of:
        - Session loading from file
        - Continuation of existing conversation
        - Proper state restoration
        """
        # Create an existing session with some history
        existing_session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        existing_session.add_user_message("Previous message")

        # Mock previous assistant response
        mock_response = Mock()
        mock_response.message = Mock()
        mock_response.message.__getitem__ = lambda self, key: "Previous response"
        mock_response.message.role = "assistant"
        mock_response.model = "test-model"
        mock_response.eval_count = 80
        mock_response.prompt_eval_count = 40
        existing_session.add_message(mock_response)
        existing_session.save_session()

        session_id = existing_session.session_id

        # Mock selector to return the existing session
        with patch('mochi_coco.chat_controller.ModelSelector') as MockSelector:
            mock_selector = Mock()
            mock_selector.select_session_or_new.return_value = (
                existing_session,  # Return the existing session
                existing_session.metadata.model,
                True,  # markdown_enabled
                False  # show_thinking
            )
            mock_selector.display_chat_history = Mock()  # Mock history display
            MockSelector.return_value = mock_selector

            # Mock single user input followed by exit
            with patch('mochi_coco.chat_controller.get_user_input', side_effect=["Continue chat", "/exit"]):
                controller = ChatController()

                # Mock renderer
                with patch.object(controller.renderer, 'render_streaming_response') as mock_render:
                    final_chunk = Mock()
                    final_chunk.message = Mock()
                    final_chunk.message.__getitem__ = lambda self, key: "Continuing our chat..."
                    final_chunk.message.role = "assistant"
                    final_chunk.model = "test-model"
                    final_chunk.eval_count = 75
                    final_chunk.prompt_eval_count = 35
                    mock_render.return_value = final_chunk

                    controller.run()

        # Verify session continuation
        assert controller.session is not None
        assert controller.session.session_id == session_id
        assert len(controller.session.messages) == 4  # Original 2 + new 2
        assert controller.session.messages[-2].content == "Continue chat"
        assert controller.session.messages[-1].role == "assistant"

        # Verify history display was called
        mock_selector.display_chat_history.assert_called_once_with(existing_session)

    def test_error_handling_during_chat_flow(
        self,
        temp_sessions_dir,
        mock_model_selector_for_integration
    ):
        """
        Test error handling during chat flow when API calls fail.

        Tests integration of:
        - Error propagation between components
        - Graceful error handling in ChatController
        - Session state preservation during errors
        """
        # Mock OllamaClient to raise an error
        with patch('mochi_coco.chat_controller.OllamaClient') as MockClientClass:
            mock_client = Mock()
            mock_client.chat_stream.side_effect = Exception("API connection failed")
            MockClientClass.return_value = mock_client

            # Mock user input
            with patch('mochi_coco.chat_controller.get_user_input', side_effect=["Hello", "/exit"]):
                controller = ChatController()

                # Capture error output
                with patch('typer.secho') as mock_secho:
                    controller.run()

                # Verify error was handled and displayed
                error_calls = [call for call in mock_secho.call_args_list
                             if 'Error:' in str(call)]
                assert len(error_calls) > 0
                assert "API connection failed" in str(error_calls[0])

        # Verify session still exists and has user message
        assert controller.session is not None
        assert len(controller.session.messages) == 1
        assert controller.session.messages[0].role == "user"
        assert controller.session.messages[0].content == "Hello"

    def test_markdown_rendering_integration(
        self,
        temp_sessions_dir,
        mock_ollama_client_integration,
        mock_model_selector_for_integration
    ):
        """
        Test integration between streaming response and markdown rendering.

        Tests integration of:
        - OllamaClient streaming
        - MarkdownRenderer processing
        - Response formatting and display
        """
        # Mock streaming response with markdown content
        def markdown_stream():
            chunk1 = Mock()
            chunk1.message = MockMessage("Here's a **bold** statement:\n\n")
            chunk1.message.role = "assistant"
            chunk1.done = False
            yield chunk1

            chunk2 = Mock()
            chunk2.message = MockMessage("```python\nprint('Hello, World!')\n```")
            chunk2.message.role = "assistant"
            chunk2.done = False
            yield chunk2

            final_chunk = Mock()
            final_chunk.message = MockMessage("")
            final_chunk.message.role = "assistant"
            final_chunk.done = True
            final_chunk.model = "test-model"
            final_chunk.eval_count = 60
            final_chunk.prompt_eval_count = 30
            yield final_chunk

        # Clear the side_effect to allow return_value to work
        mock_ollama_client_integration.chat_stream.side_effect = None
        mock_ollama_client_integration.chat_stream.return_value = markdown_stream()

        with patch('mochi_coco.chat_controller.get_user_input', side_effect=["Show me some code", "/exit"]):
            controller = ChatController()

            # Use real MarkdownRenderer to test integration
            controller.renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)

            # Capture the rendered output
            rendered_content = []
            original_render = controller.renderer.render_streaming_response

            def capture_render(text_stream):
                result = original_render(text_stream)
                # The final content should include the complete text
                if result and hasattr(result.message, '__getitem__'):
                    full_content = result.message['content'] if callable(result.message.__getitem__) else ""
                    rendered_content.append(full_content)
                return result

            with patch.object(controller.renderer, 'render_streaming_response', side_effect=capture_render):
                controller.run()

        # Verify session contains the complete message
        assert controller.session is not None
        assert len(controller.session.messages) >= 2
        assistant_message = controller.session.messages[1]
        assert assistant_message.role == "assistant"
        # Content should include both markdown parts
        expected_content = "Here's a **bold** statement:\n\n```python\nprint('Hello, World!')\n```"
        assert assistant_message.content == expected_content

    def test_thinking_blocks_integration(
        self,
        temp_sessions_dir,
        mock_ollama_client_integration
    ):
        """
        Test integration of thinking blocks in responses.

        Tests integration of:
        - Streaming response with thinking blocks
        - MarkdownRenderer thinking block processing
        - Different rendering modes for thinking blocks
        """
        # Mock selector to enable thinking blocks
        with patch('mochi_coco.chat_controller.ModelSelector') as MockSelector:
            mock_selector = Mock()
            mock_selector.select_session_or_new.return_value = (
                None,  # New session
                "test-model",
                True,  # markdown_enabled
                True   # show_thinking = True
            )
            MockSelector.return_value = mock_selector

            # Mock streaming response with thinking blocks
            def thinking_stream():
                chunk1 = Mock()
                chunk1.message = MockMessage("<thinking>\nLet me think about this question...\n</thinking>\n\n")
                chunk1.message.role = "assistant"
                chunk1.done = False
                yield chunk1

                chunk2 = Mock()
                chunk2.message = MockMessage("Here's my response after thinking.")
                chunk2.message.role = "assistant"
                chunk2.done = False
                yield chunk2

                final_chunk = Mock()
                final_chunk.message = MockMessage("")
                final_chunk.message.role = "assistant"
                final_chunk.done = True
                final_chunk.model = "test-model"
                final_chunk.eval_count = 75
                final_chunk.prompt_eval_count = 35
                yield final_chunk

            # Clear the side_effect to allow return_value to work
            mock_ollama_client_integration.chat_stream.side_effect = None
            mock_ollama_client_integration.chat_stream.return_value = thinking_stream()

            with patch('mochi_coco.chat_controller.get_user_input', side_effect=["What should I think about?", "/exit"]):
                controller = ChatController()

                # Ensure renderer is set to show thinking blocks
                controller.renderer.set_show_thinking(True)
                controller.renderer.set_mode(RenderingMode.MARKDOWN)

                controller.run()

        # Verify session contains complete content including thinking blocks
        assert controller.session is not None
        assistant_message = controller.session.messages[1]
        expected_content = "<thinking>\nLet me think about this question...\n</thinking>\n\nHere's my response after thinking."
        assert assistant_message.content == expected_content

    def test_session_persistence_across_multiple_messages(
        self,
        temp_sessions_dir,
        mock_ollama_client_integration,
        mock_model_selector_for_integration
    ):
        """
        Test that session persistence works correctly across multiple message exchanges.

        Tests integration of:
        - Multiple message exchanges
        - Session updates after each message
        - File persistence integrity
        - Metadata updates
        """
        # Create sequence of user inputs
        user_inputs = [
            "First message",
            "Second message",
            "Third message",
            "/exit"
        ]

        with patch('mochi_coco.chat_controller.get_user_input', side_effect=user_inputs):
            controller = ChatController()

            # Mock renderer to return consistent responses
            response_count = 0
            def mock_render_response(text_stream):
                nonlocal response_count
                response_count += 1

                # Consume the stream to simulate real rendering
                content_parts = []
                final_chunk = None
                for chunk in text_stream:
                    if chunk.done:
                        final_chunk = chunk
                        break
                    content_parts.append(chunk.message.content)

                # Create a realistic final chunk with accumulated content
                if final_chunk:
                    # Create properly structured mock chunk
                    mock_chunk = Mock()
                    mock_chunk.message = Mock()
                    mock_chunk.message.role = "assistant"
                    mock_chunk.message.__getitem__ = lambda self, key: f"Response {response_count}" if key == 'content' else ""
                    mock_chunk.message.content = f"Response {response_count}"
                    mock_chunk.model = "test-model"
                    mock_chunk.eval_count = 50 + response_count * 5
                    mock_chunk.prompt_eval_count = 25 + response_count * 2
                    mock_chunk.done = True

                    return mock_chunk

                return final_chunk

            with patch.object(controller.renderer, 'render_streaming_response', side_effect=mock_render_response):
                controller.run()

        # Verify final session state
        session = controller.session
        assert session is not None
        assert len(session.messages) == 6  # 3 user + 3 assistant messages

        # Verify message sequence
        expected_sequence = [
            ("user", "First message"),
            ("assistant", "Response 1"),
            ("user", "Second message"),
            ("assistant", "Response 2"),
            ("user", "Third message"),
            ("assistant", "Response 3")
        ]

        for i, (expected_role, expected_content) in enumerate(expected_sequence):
            assert session.messages[i].role == expected_role
            if expected_role == "user":
                assert session.messages[i].content == expected_content
            else:
                assert expected_content in session.messages[i].content

        # Verify session metadata
        assert session.metadata.message_count == 6
        assert session.metadata.model == "test-model"

        # Verify session was persisted correctly
        session_file = session.session_file
        assert session_file.exists()

        # Load session from file and verify integrity
        from mochi_coco.chat.session import ChatSession
        loaded_session = ChatSession(
            model="",
            session_id=session.session_id,
            sessions_dir=str(session.sessions_dir)  # Use the same directory as the original session
        )
        assert loaded_session.load_session() is True
        assert len(loaded_session.messages) == 6
        assert loaded_session.metadata.message_count == 6

    @pytest.mark.slow
    def test_concurrent_chat_sessions(self, temp_sessions_dir, mock_ollama_client_integration):
        """
        Test that multiple chat sessions can operate concurrently without interference.

        Tests integration of:
        - Multiple session instances
        - File system concurrency
        - Session isolation
        """
        # Create two separate sessions
        session1_id = "session001"
        session2_id = "session002"

        session1 = ChatSession(model="test-model", session_id=session1_id, sessions_dir=temp_sessions_dir)
        session2 = ChatSession(model="test-model", session_id=session2_id, sessions_dir=temp_sessions_dir)

        # Add different messages to each session
        session1.add_user_message("Message from session 1")
        session2.add_user_message("Message from session 2")

        # Mock responses for each
        mock_response1 = Mock()
        mock_response1.message = Mock()
        mock_response1.message.__getitem__ = lambda self, key: "Response to session 1"
        mock_response1.message.role = "assistant"
        mock_response1.model = "test-model"
        mock_response1.eval_count = 80
        mock_response1.prompt_eval_count = 40

        mock_response2 = Mock()
        mock_response2.message = Mock()
        mock_response2.message.__getitem__ = lambda self, key: "Response to session 2"
        mock_response2.message.role = "assistant"
        mock_response2.model = "test-model"
        mock_response2.eval_count = 90
        mock_response2.prompt_eval_count = 45

        session1.add_message(mock_response1)
        session2.add_message(mock_response2)

        # Both sessions should have different content
        assert len(session1.messages) == 2
        assert len(session2.messages) == 2
        assert session1.messages[0].content == "Message from session 1"
        assert session2.messages[0].content == "Message from session 2"
        assert session1.messages[1].content == "Response to session 1"
        assert session2.messages[1].content == "Response to session 2"

        # Both session files should exist
        session1_file = Path(temp_sessions_dir) / f"{session1_id}.json"
        session2_file = Path(temp_sessions_dir) / f"{session2_id}.json"
        assert session1_file.exists()
        assert session2_file.exists()

        # Load both sessions independently and verify isolation
        loaded_session1 = ChatSession(model="", session_id=session1_id, sessions_dir=temp_sessions_dir)
        loaded_session2 = ChatSession(model="", session_id=session2_id, sessions_dir=temp_sessions_dir)

        assert loaded_session1.load_session() is True
        assert loaded_session2.load_session() is True

        # Verify they maintained separate content
        assert loaded_session1.messages[0].content == "Message from session 1"
        assert loaded_session2.messages[0].content == "Message from session 2"
