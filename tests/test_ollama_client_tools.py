import pytest
from unittest.mock import Mock, patch, MagicMock

from mochi_coco.ollama.client import OllamaClient

class TestOllamaClientTools:

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_stream_without_tools(self, mock_client_class):
        """Test backward compatibility - streaming without tools."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock response
        mock_response = MagicMock()
        mock_response.message.content = "Hi"
        mock_client.chat.return_value = [mock_response]

        # Call without tools (backward compatibility)
        list(client.chat_stream("test-model", messages))

        # Verify client.chat was called without tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True
        )

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_stream_with_tools(self, mock_client_class):
        """Test streaming with tools parameter."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Create a mock tool
        def test_tool():
            """Test tool"""
            return "result"

        # Setup mock response with tool call
        mock_response = MagicMock()
        mock_response.message.tool_calls = [
            MagicMock(function=MagicMock(name="test_tool", arguments={}))
        ]
        mock_client.chat.return_value = [mock_response]

        # Call with tools
        list(client.chat_stream("test-model", messages, tools=[test_tool]))

        # Verify client.chat was called with tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            tools=[test_tool]
        )

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_stream_with_think(self, mock_client_class):
        """Test streaming with think parameter."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        mock_client.chat.return_value = []

        # Call with think parameter
        list(client.chat_stream("test-model", messages, think=True))

        # Verify client.chat was called with think parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            think=True
        )

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_stream_with_all_params(self, mock_client_class):
        """Test streaming with all optional parameters."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        def test_tool():
            return "result"

        mock_client.chat.return_value = []

        # Call with all parameters
        list(client.chat_stream("test-model", messages,
                               tools=[test_tool], think=True))

        # Verify all parameters were passed
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            tools=[test_tool],
            think=True
        )

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_without_tools(self, mock_client_class):
        """Test non-streaming chat without tools."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock response
        mock_response = MagicMock()
        mock_response.message.content = "Hi"
        mock_client.chat.return_value = mock_response

        # Call without tools
        result = client.chat("test-model", messages)

        # Verify client.chat was called without tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False
        )
        assert result == mock_response

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_with_tools(self, mock_client_class):
        """Test non-streaming chat with tools parameter."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        def test_tool():
            """Test tool"""
            return "result"

        # Setup mock response
        mock_response = MagicMock()
        mock_response.message.content = "Hi"
        mock_client.chat.return_value = mock_response

        # Call with tools
        result = client.chat("test-model", messages, tools=[test_tool])

        # Verify client.chat was called with tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            tools=[test_tool]
        )
        assert result == mock_response

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_with_think(self, mock_client_class):
        """Test non-streaming chat with think parameter."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = MagicMock()
        mock_client.chat.return_value = mock_response

        # Call with think parameter
        result = client.chat("test-model", messages, think=True)

        # Verify client.chat was called with think parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            think=True
        )
        assert result == mock_response

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_with_all_params(self, mock_client_class):
        """Test non-streaming chat with all optional parameters."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        def test_tool():
            return "result"

        mock_response = MagicMock()
        mock_client.chat.return_value = mock_response

        # Call with all parameters
        result = client.chat("test-model", messages,
                           tools=[test_tool], think=True)

        # Verify all parameters were passed
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            tools=[test_tool],
            think=True
        )
        assert result == mock_response

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_stream_error_handling(self, mock_client_class):
        """Test error handling in streaming chat."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock to raise exception
        mock_client.chat.side_effect = Exception("Connection error")

        # Verify exception is properly re-raised
        with pytest.raises(Exception, match="Chat failed: Connection error"):
            list(client.chat_stream("test-model", messages))

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_error_handling(self, mock_client_class):
        """Test error handling in non-streaming chat."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock to raise exception
        mock_client.chat.side_effect = Exception("Connection error")

        # Verify exception is properly re-raised
        with pytest.raises(Exception, match="Chat failed: Connection error"):
            client.chat("test-model", messages)

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_stream_tool_object_support(self, mock_client_class):
        """Test streaming with Tool objects."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Create a mock Tool object
        mock_tool = MagicMock()
        mock_tool.type = "function"

        mock_client.chat.return_value = []

        # Call with Tool object
        list(client.chat_stream("test-model", messages, tools=[mock_tool]))

        # Verify client.chat was called with Tool object
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            tools=[mock_tool]
        )

    @patch('mochi_coco.ollama.client.Client')
    def test_chat_tool_object_support(self, mock_client_class):
        """Test non-streaming chat with Tool objects."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Create a mock Tool object
        mock_tool = MagicMock()
        mock_tool.type = "function"

        mock_response = MagicMock()
        mock_client.chat.return_value = mock_response

        # Call with Tool object
        result = client.chat("test-model", messages, tools=[mock_tool])

        # Verify client.chat was called with Tool object
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            tools=[mock_tool]
        )
        assert result == mock_response

    @patch('mochi_coco.ollama.client.Client')
    def test_empty_tools_list(self, mock_client_class):
        """Test behavior with empty tools list."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        mock_client.chat.return_value = []

        # Call with empty tools list
        list(client.chat_stream("test-model", messages, tools=[]))

        # Verify empty tools list is passed
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            tools=[]
        )
