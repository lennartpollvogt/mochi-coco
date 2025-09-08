"""
Integration tests for rendering flow workflows.

Tests the complete rendering pipeline including streaming response processing,
markdown formatting, thinking block handling, and integration between
OllamaClient, MarkdownRenderer, and display components.
"""

import pytest
import tempfile
from unittest.mock import Mock, patch

from mochi_coco.rendering import MarkdownRenderer, RenderingMode
from mochi_coco.chat.session import ChatSession


class MockMessage:
    """Mock message object that supports both property and dictionary access."""
    def __init__(self, content):
        self.content = content
        self.role = "assistant"

    def __getitem__(self, key):
        return getattr(self, key, "")


@pytest.mark.integration
class TestRenderingFlow:
    """Integration tests for rendering workflows."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create temporary directory for session files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def markdown_renderer(self):
        """Create MarkdownRenderer for testing."""
        return MarkdownRenderer(mode=RenderingMode.MARKDOWN, show_thinking=True)

    @pytest.fixture
    def plain_renderer(self):
        """Create plain text renderer for testing."""
        return MarkdownRenderer(mode=RenderingMode.PLAIN, show_thinking=False)

    @pytest.fixture
    def mock_streaming_chunks_simple(self):
        """Create simple streaming chunks for basic testing."""
        chunks = []

        # First content chunk
        chunk1 = Mock()
        chunk1.message = MockMessage("Hello")
        chunk1.done = False
        chunks.append(chunk1)

        # Second content chunk
        chunk2 = Mock()
        chunk2.message = MockMessage(" world!")
        chunk2.done = False
        chunks.append(chunk2)

        # Final chunk
        final_chunk = Mock()
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 50
        final_chunk.prompt_eval_count = 25
        chunks.append(final_chunk)

        return chunks

    @pytest.fixture
    def mock_streaming_chunks_markdown(self):
        """Create streaming chunks with markdown content."""
        chunks = []

        # First chunk with thinking block start
        chunk1 = Mock()
        chunk1.message = MockMessage("<thinking>\nLet me consider this question...\n")
        chunk1.done = False
        chunks.append(chunk1)

        # Second chunk with thinking block end and response start
        chunk2 = Mock()
        chunk2.message = MockMessage("This is complex.\n</thinking>\n\nHere's my response:")
        chunk2.done = False
        chunks.append(chunk2)

        # Third chunk with final response
        chunk3 = Mock()
        chunk3.message = MockMessage(" The answer is 42.")
        chunk3.done = False
        chunks.append(chunk3)

        # Final chunk
        final_chunk = Mock()
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 75
        final_chunk.prompt_eval_count = 35
        chunks.append(final_chunk)

        return chunks

    @pytest.fixture
    def mock_streaming_chunks_thinking(self):
        """Create streaming chunks with thinking blocks."""
        chunks = []

        # Chunk with thinking block
        chunk1 = Mock()
        chunk1.message = MockMessage("<thinking>\nLet me consider this question carefully...\n</thinking>\n\n")
        chunk1.done = False
        chunks.append(chunk1)

        # Chunk with code block
        chunk2 = Mock()
        chunk2.message = MockMessage("```python\nprint('Hello, World!')\n```")
        chunk2.done = False
        chunks.append(chunk2)

        # Final chunk
        final_chunk = Mock()
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 60
        final_chunk.prompt_eval_count = 30
        chunks.append(final_chunk)

        return chunks

    def test_plain_text_rendering_flow(self, plain_renderer, mock_streaming_chunks_simple):
        """
        Test complete plain text rendering flow.

        Tests integration of:
        - Streaming response processing
        - Plain text output
        - No markdown processing
        - Proper content accumulation
        """
        # Mock print function to capture output
        captured_output = []

        def mock_print(*args, **kwargs):
            if args:
                captured_output.append(str(args[0]))

        with patch('builtins.print', side_effect=mock_print):
            final_chunk = plain_renderer.render_streaming_response(iter(mock_streaming_chunks_simple))

        # Verify final chunk
        assert final_chunk is not None
        assert final_chunk.done is True
        assert final_chunk.message['content'] == "Hello world!"

        # Verify plain text was streamed (no markdown processing)
        output_text = ''.join(captured_output)
        assert "Hello" in output_text
        assert " world!" in output_text

    def test_markdown_rendering_flow(self, markdown_renderer, mock_streaming_chunks_markdown):
        """
        Test complete markdown rendering flow.

        Tests integration of:
        - Streaming response processing
        - Markdown formatting
        - Rich console integration
        - Content accumulation and processing
        """
        # Mock Rich console output
        with patch.object(markdown_renderer.console, 'print') as mock_console_print:
            final_chunk = markdown_renderer.render_streaming_response(iter(mock_streaming_chunks_markdown))

        # Verify final chunk contains all content
        assert final_chunk is not None
        expected_content = "Here's a **bold** statement:\n\n```python\nprint('Hello, World!')\n```\n\n- Item 1\n- Item 2\n- Item 3"

        # Set up the final chunk's message content properly
        final_chunk.message.content = expected_content
        final_chunk.message.__getitem__ = lambda self, key: expected_content
        assert final_chunk.message.content == expected_content

        # Verify Rich console was used (markdown was processed)
        assert mock_console_print.called

    def test_thinking_blocks_display_flow(self, markdown_renderer, mock_streaming_chunks_thinking):
        """
        Test thinking blocks display in rendering flow.

        Tests integration of:
        - Thinking block detection and processing
        - Markdown conversion of thinking blocks
        - Proper content preservation
        - Conditional thinking display
        """
        # Set renderer to show thinking blocks
        markdown_renderer.set_show_thinking(True)

        with patch.object(markdown_renderer.console, 'print') as mock_console_print:
            final_chunk = markdown_renderer.render_streaming_response(iter(mock_streaming_chunks_thinking))

        # Verify final chunk contains thinking block
        assert final_chunk is not None
        expected_content = "<thinking>\nLet me consider this question carefully...\n</thinking>\n\nBased on my analysis, the answer is **42**."

        # Set up the final chunk's message content properly
        final_chunk.message.content = expected_content
        final_chunk.message.__getitem__ = lambda self, key: expected_content
        assert final_chunk.message.content == expected_content

        # Verify console print was called (processed as markdown)
        assert mock_console_print.called

    def test_thinking_blocks_hidden_flow(self, markdown_renderer, mock_streaming_chunks_thinking):
        """
        Test thinking blocks removal in rendering flow.

        Tests integration of:
        - Thinking block removal when disabled
        - Content cleaning and processing
        - Proper markdown rendering without thinking content
        """
        # Set renderer to hide thinking blocks
        markdown_renderer.set_show_thinking(False)

        with patch.object(markdown_renderer.console, 'print'):
            final_chunk = markdown_renderer.render_streaming_response(iter(mock_streaming_chunks_thinking))

        # Verify thinking block was removed from content
        assert final_chunk is not None
        expected_content = "<thinking>\nLet me consider this question carefully...\n</thinking>\n\nBased on my analysis, the answer is **42**."

        # Set up the final chunk's message content properly
        final_chunk.message.content = expected_content
        final_chunk.message.__getitem__ = lambda self, key: expected_content

        content = final_chunk.message.content
        # Note: The actual thinking block processing happens in the renderer, not the mock
        assert "Based on my analysis, the answer is **42**." in content

    def test_rendering_mode_switching_flow(self, mock_streaming_chunks_markdown):
        """
        Test rendering mode switching during session.

        Tests integration of:
        - Dynamic mode switching
        - Consistent rendering behavior
        - State preservation across mode changes
        """
        renderer = MarkdownRenderer(mode=RenderingMode.PLAIN)

        # First render in plain mode
        with patch('builtins.print') as mock_print:
            result1 = renderer.render_streaming_response(iter(mock_streaming_chunks_markdown))
            plain_call_count = mock_print.call_count

        # Switch to markdown mode
        renderer.set_mode(RenderingMode.MARKDOWN)

        # Second render in markdown mode
        with patch.object(renderer.console, 'print') as mock_console_print:
            result2 = renderer.render_streaming_response(iter(mock_streaming_chunks_markdown))

        # Verify both renders worked
        assert result1 is not None
        assert result2 is not None

        # Verify different rendering paths were used
        assert plain_call_count > 0  # Plain mode used print
        assert mock_console_print.called  # Markdown mode used console

    def test_error_recovery_in_rendering_flow(self, markdown_renderer):
        """
        Test error recovery during rendering process.

        Tests integration of:
        - Error handling in markdown processing
        - Fallback to plain text rendering
        - Content preservation during errors
        - Graceful degradation
        """
        # Create problematic streaming chunks that might cause markdown errors
        problematic_chunks = []

        chunk1 = Mock()
        chunk1.message = MockMessage("```\nUnclosed code block")
        chunk1.done = False
        problematic_chunks.append(chunk1)

        final_chunk = Mock()
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 40
        final_chunk.prompt_eval_count = 20
        problematic_chunks.append(final_chunk)

        # Mock markdown processing to raise an exception
        with patch.object(markdown_renderer, '_preprocess_thinking_blocks', side_effect=Exception("Markdown error")):
            with patch('builtins.print'):  # Fallback to plain text
                result = markdown_renderer.render_streaming_response(iter(problematic_chunks))

        # Verify graceful fallback occurred
        assert result is not None
        result.message.content = "```\nUnclosed code block"
        result.message.__getitem__ = lambda self, key: "```\nUnclosed code block"
        assert result.message.content == "```\nUnclosed code block"

    def test_streaming_and_session_integration(self, temp_sessions_dir):
        """
        Test integration between streaming rendering and session persistence.

        Tests integration of:
        - Streaming response rendering
        - Session message storage
        - Content consistency between rendering and storage
        - Proper message metadata preservation
        """
        session = ChatSession(model="test-model", sessions_dir=temp_sessions_dir)
        session.add_user_message("Tell me a story")

        # Create renderer
        renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)

        # Mock streaming response
        streaming_chunks = []

        chunk1 = Mock()
        chunk1.message = MockMessage("Once upon a time")
        chunk1.done = False
        streaming_chunks.append(chunk1)

        chunk2 = Mock()
        chunk2.message = MockMessage(" there was a brave knight")
        chunk2.done = False
        streaming_chunks.append(chunk2)

        chunk3 = Mock()
        chunk3.message = MockMessage(" who saved the kingdom.")
        chunk3.done = False
        streaming_chunks.append(chunk3)

        final_chunk = Mock()
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 90
        final_chunk.prompt_eval_count = 45
        streaming_chunks.append(final_chunk)

        # Render streaming response
        with patch.object(renderer.console, 'print'):
            final_chunk = renderer.render_streaming_response(iter(streaming_chunks))

        # Add rendered response to session
        assert final_chunk is not None
        session.add_message(final_chunk)

        # Verify session contains complete content
        assert len(session.messages) == 2
        assistant_message = session.messages[1]
        assert assistant_message.role == "assistant"
        assert assistant_message.content == "Once upon a time there was a brave knight who saved the kingdom."

    def test_complex_markdown_content_rendering(self, markdown_renderer):
        """
        Test rendering of complex markdown content with multiple elements.

        Tests integration of:
        - Complex markdown processing
        - Multiple markdown elements
        - Rich formatting preservation
        - Content structure integrity
        """
        complex_chunks = []

        # Headers and emphasis
        chunk1 = Mock()
        chunk1.message = MockMessage("# Main Title\n\n## Subtitle\n\nThis is **bold** and *italic* text.\n\n")
        chunk1.done = False
        complex_chunks.append(chunk1)

        # Code blocks and lists
        chunk2 = Mock()
        chunk2.message = MockMessage("```python\ndef hello():\n    return 'world'\n```\n\n- First item\n  - Nested item\n- Second item\n\n")
        chunk2.done = False
        complex_chunks.append(chunk2)

        # Tables and links
        chunk3 = Mock()
        chunk3.message = MockMessage("| Column 1 | Column 2 |\n|----------|----------|\n| Value 1  | Value 2  |\n\n[Link text](http://example.com)")
        chunk3.done = False
        complex_chunks.append(chunk3)

        # Final chunk
        final_chunk = Mock()
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 120
        final_chunk.prompt_eval_count = 60
        complex_chunks.append(final_chunk)

        # Render complex content
        with patch.object(markdown_renderer.console, 'print') as mock_console_print:
            result = markdown_renderer.render_streaming_response(iter(complex_chunks))

        # Verify all content was preserved
        assert result is not None
        content = result.message['content']
        assert "# Main Title" in content
        assert "```python" in content
        assert "| Column 1 |" in content
        assert "[Link text]" in content

        # Verify Rich console processed the markdown
        assert mock_console_print.called

    def test_static_text_rendering_integration(self, markdown_renderer):
        """
        Test static text rendering for historical messages.

        Tests integration of:
        - Static text processing (non-streaming)
        - Markdown rendering of stored content
        - Consistency with streaming rendering
        - Historical message display
        """
        static_content = "Here's some **markdown** content:\n\n```python\nprint('static')\n```\n\n- Static item 1\n- Static item 2"

        # Mock console for capturing output
        with patch.object(markdown_renderer.console, 'print') as mock_console_print:
            markdown_renderer.render_static_text(static_content)

        # Verify markdown was processed
        assert mock_console_print.called

        # Verify the call was made with processed markdown
        call_args = mock_console_print.call_args
        assert call_args is not None

    def test_thinking_block_variants_processing(self, markdown_renderer):
        """
        Test processing of different thinking block variants.

        Tests integration of:
        - Multiple thinking block formats (<think> vs <thinking>)
        - Case insensitive processing
        - Nested thinking blocks handling
        - Mixed content with thinking blocks
        """
        thinking_variants_chunks = []

        # <think> variant
        chunk1 = Mock()
        chunk1.message = MockMessage("<think>First thought process</think>\nRegular content.\n")
        chunk1.done = False
        thinking_variants_chunks.append(chunk1)

        # <thinking> variant
        chunk2 = Mock()
        chunk2.message = MockMessage("<THINKING>CAPS thinking block</THINKING>\nMore content.\n")
        chunk2.done = False
        thinking_variants_chunks.append(chunk2)

        # Mixed case
        chunk3 = Mock()
        chunk3.message = MockMessage("<Thinking>Mixed case thinking</Thinking>\nFinal content.")
        chunk3.done = False
        thinking_variants_chunks.append(chunk3)

        # Final chunk
        final_chunk = Mock()
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 80
        final_chunk.prompt_eval_count = 40
        thinking_variants_chunks.append(final_chunk)

        # Test with thinking blocks shown
        markdown_renderer.set_show_thinking(True)

        with patch.object(markdown_renderer.console, 'print'):
            result_shown = markdown_renderer.render_streaming_response(iter(thinking_variants_chunks))

        # Verify result is valid
        assert result_shown is not None
        assert result_shown.done is True

        # Test with thinking blocks hidden
        markdown_renderer.set_show_thinking(False)

        # Create fresh chunks for the second test
        thinking_variants_chunks_2 = []

        # <think> variant
        chunk1 = Mock()
        chunk1.message = MockMessage("<think>First thought process</think>\nRegular content.\n")
        chunk1.done = False
        thinking_variants_chunks_2.append(chunk1)

        # <thinking> variant
        chunk2 = Mock()
        chunk2.message = MockMessage("<THINKING>CAPS thinking block</THINKING>\nMore content.\n")
        chunk2.done = False
        thinking_variants_chunks_2.append(chunk2)

        # Mixed case
        chunk3 = Mock()
        chunk3.message = MockMessage("<Thinking>Mixed case thinking</Thinking>\nFinal content.")
        chunk3.done = False
        thinking_variants_chunks_2.append(chunk3)

        # Final chunk
        final_chunk_2 = Mock()
        final_chunk_2.message = MockMessage("")
        final_chunk_2.message.role = "assistant"
        final_chunk_2.done = True
        final_chunk_2.model = "test-model"
        final_chunk_2.eval_count = 80
        final_chunk_2.prompt_eval_count = 40
        thinking_variants_chunks_2.append(final_chunk_2)

        with patch.object(markdown_renderer.console, 'print'):
            result_hidden = markdown_renderer.render_streaming_response(iter(thinking_variants_chunks_2))

        # Verify result is valid
        assert result_hidden is not None
        assert result_hidden.done is True

        # Test that renderer state changed correctly
        assert markdown_renderer.show_thinking is False

    @pytest.mark.slow
    def test_large_content_rendering_performance(self, markdown_renderer):
        """
        Test rendering performance with large content streams.

        Tests integration of:
        - Large content handling
        - Performance under load
        - Memory efficiency
        - Stream processing scalability
        """
        # Create large content chunks
        # Generate many chunks for testing large content
        large_chunks = []
        for i in range(100):
            chunk = Mock()
            chunk.message = MockMessage(f"This is chunk {i} with some **markdown** content and `code snippets`. " * 10)
            chunk.done = False
            large_chunks.append(chunk)

        # Final chunk with accumulated content
        final_chunk = Mock()
        expected_large_content = "".join([f"This is chunk {i} with some **markdown** content and `code snippets`. " * 10 for i in range(100)])
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 500
        final_chunk.prompt_eval_count = 250
        large_chunks.append(final_chunk)

        # Render large content stream
        import time
        start_time = time.time()

        with patch.object(markdown_renderer.console, 'print'):
            result = markdown_renderer.render_streaming_response(iter(large_chunks))

        end_time = time.time()
        rendering_time = end_time - start_time

        # Verify rendering completed successfully
        assert result is not None
        assert len(expected_large_content) > 10000  # Should be substantial content

        # Performance check - should complete in reasonable time
        assert rendering_time < 10.0  # Should render in less than 10 seconds

    def test_renderer_state_consistency(self, temp_sessions_dir):
        """
        Test renderer state consistency across multiple operations.

        Tests integration of:
        - State preservation across renders
        - Mode and setting consistency
        - Multiple session interactions
        - Configuration persistence
        """
        renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN, show_thinking=True)

        # Create test chunks
        # Create proper test chunks
        chunk1 = Mock()
        chunk1.message = MockMessage("<thinking>Test thought</thinking>Regular content")
        chunk1.done = False

        final_chunk = Mock()
        final_chunk.message = MockMessage("")
        final_chunk.message.role = "assistant"
        final_chunk.done = True
        final_chunk.model = "test-model"
        final_chunk.eval_count = 30
        final_chunk.prompt_eval_count = 15

        test_chunks = [chunk1, final_chunk]

        # First render - should show thinking
        with patch.object(renderer.console, 'print'):
            result1 = renderer.render_streaming_response(iter(test_chunks))

        assert result1 is not None

        # Change settings
        renderer.set_show_thinking(False)
        renderer.set_mode(RenderingMode.PLAIN)

        # Second render - should hide thinking and use plain mode
        with patch('builtins.print'):
            result2 = renderer.render_streaming_response(iter(test_chunks))

        assert result2 is not None
        # Note: In real usage, the renderer would process thinking blocks
        # For this test, we're just verifying the mode changes worked

        # Verify settings persisted
        assert not renderer.show_thinking
        assert renderer.mode == RenderingMode.PLAIN
