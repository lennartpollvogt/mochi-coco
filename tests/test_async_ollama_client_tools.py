import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import anyio

from mochi_coco.ollama.async_client import AsyncOllamaClient


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_stream_without_tools(mock_client_class):
    """Test backward compatibility - async streaming without tools."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock response
        mock_response = MagicMock()
        mock_response.message.content = "Hi"

        async def mock_async_generator():
            yield mock_response

        mock_client.chat.return_value = mock_async_generator()

        # Call without tools (backward compatibility)
        chunks = []
        async for chunk in client.chat_stream("test-model", messages):
            chunks.append(chunk)

        # Verify client.chat was called without tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True
        )

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_stream_with_tools(mock_client_class):
    """Test async streaming with tools parameter."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
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

        async def mock_async_generator():
            yield mock_response

        mock_client.chat.return_value = mock_async_generator()

        # Call with tools
        chunks = []
        async for chunk in client.chat_stream("test-model", messages, tools=[test_tool]):
            chunks.append(chunk)

        # Verify client.chat was called with tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            tools=[test_tool]
        )

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_stream_with_think(mock_client_class):
    """Test async streaming with think parameter."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        async def mock_async_generator():
            return
            yield  # This makes it an async generator but yields nothing

        mock_client.chat.return_value = mock_async_generator()

        # Call with think parameter
        chunks = []
        async for chunk in client.chat_stream("test-model", messages, think=True):
            chunks.append(chunk)

        # Verify client.chat was called with think parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            think=True
        )

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_stream_with_all_params(mock_client_class):
    """Test async streaming with all optional parameters."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        def test_tool():
            return "result"

        async def mock_async_generator():
            return
            yield  # This makes it an async generator but yields nothing

        mock_client.chat.return_value = mock_async_generator()

        # Call with all parameters
        chunks = []
        async for chunk in client.chat_stream("test-model", messages,
                                           tools=[test_tool], think=True):
            chunks.append(chunk)

        # Verify all parameters were passed
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            tools=[test_tool],
            think=True
        )

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_single_without_tools(mock_client_class):
    """Test async non-streaming chat_single without tools (backward compatibility)."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock response
        mock_response = MagicMock()
        mock_response.message.content = "Hi"
        mock_client.chat.return_value = mock_response

        # Call without tools
        result = await client.chat_single("test-model", messages)

        # Verify client.chat was called without tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            format=None
        )
        assert result == mock_response

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_single_with_tools(mock_client_class):
    """Test async chat_single with tools parameter."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        def test_tool():
            """Test tool"""
            return "result"

        # Setup mock response
        mock_response = MagicMock()
        mock_response.message.content = "Hi"
        mock_client.chat.return_value = mock_response

        # Call with tools
        result = await client.chat_single("test-model", messages, tools=[test_tool])

        # Verify client.chat was called with tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            format=None,
            tools=[test_tool]
        )
        assert result == mock_response

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_without_tools(mock_client_class):
    """Test async non-streaming chat without tools."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock response
        mock_response = MagicMock()
        mock_response.message.content = "Hi"
        mock_client.chat.return_value = mock_response

        # Call without tools
        result = await client.chat("test-model", messages)

        # Verify client.chat was called without tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False
        )
        assert result == mock_response

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_with_tools(mock_client_class):
    """Test async non-streaming chat with tools parameter."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        def test_tool():
            """Test tool"""
            return "result"

        # Setup mock response
        mock_response = MagicMock()
        mock_response.message.content = "Hi"
        mock_client.chat.return_value = mock_response

        # Call with tools
        result = await client.chat("test-model", messages, tools=[test_tool])

        # Verify client.chat was called with tools parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            tools=[test_tool]
        )
        assert result == mock_response

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_with_think(mock_client_class):
    """Test async non-streaming chat with think parameter."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = MagicMock()
        mock_client.chat.return_value = mock_response

        # Call with think parameter
        result = await client.chat("test-model", messages, think=True)

        # Verify client.chat was called with think parameter
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            think=True
        )
        assert result == mock_response

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_with_all_params(mock_client_class):
    """Test async non-streaming chat with all optional parameters."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        def test_tool():
            return "result"

        mock_response = MagicMock()
        mock_client.chat.return_value = mock_response

        # Call with all parameters
        result = await client.chat("test-model", messages,
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

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_stream_error_handling(mock_client_class):
    """Test error handling in async streaming chat."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock to raise exception
        mock_client.chat.side_effect = Exception("Connection error")

        # Verify exception is properly re-raised
        with pytest.raises(Exception):
            chunks = []
            async for chunk in client.chat_stream("test-model", messages):
                chunks.append(chunk)

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_single_error_handling(mock_client_class):
    """Test error handling in async chat_single."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock to raise exception
        mock_client.chat.side_effect = Exception("Connection error")

        # Verify exception is properly re-raised
        with pytest.raises(Exception):
            await client.chat_single("test-model", messages)

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_error_handling(mock_client_class):
    """Test error handling in async non-streaming chat."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Setup mock to raise exception
        mock_client.chat.side_effect = Exception("Connection error")

        # Verify exception is properly re-raised
        with pytest.raises(Exception):
            await client.chat("test-model", messages)

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_stream_tool_object_support(mock_client_class):
    """Test async streaming with Tool objects."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Create a mock Tool object
        mock_tool = MagicMock()
        mock_tool.type = "function"

        async def mock_async_generator():
            return
            yield  # This makes it an async generator but yields nothing

        mock_client.chat.return_value = mock_async_generator()

        # Call with Tool object
        chunks = []
        async for chunk in client.chat_stream("test-model", messages, tools=[mock_tool]):
            chunks.append(chunk)

        # Verify client.chat was called with Tool object
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            tools=[mock_tool]
        )

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_chat_tool_object_support(mock_client_class):
    """Test async non-streaming chat with Tool objects."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        # Create a mock Tool object
        mock_tool = MagicMock()
        mock_tool.type = "function"

        mock_response = MagicMock()
        mock_client.chat.return_value = mock_response

        # Call with Tool object
        result = await client.chat("test-model", messages, tools=[mock_tool])

        # Verify client.chat was called with Tool object
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=False,
            tools=[mock_tool]
        )
        assert result == mock_response

    anyio.run(_test)


@patch('mochi_coco.ollama.async_client.AsyncClient')
def test_empty_tools_list(mock_client_class):
    """Test async behavior with empty tools list."""
    async def _test():
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        client = AsyncOllamaClient()
        messages = [{"role": "user", "content": "Hello"}]

        async def mock_async_generator():
            return
            yield  # This makes it an async generator but yields nothing

        mock_client.chat.return_value = mock_async_generator()

        # Call with empty tools list
        chunks = []
        async for chunk in client.chat_stream("test-model", messages, tools=[]):
            chunks.append(chunk)

        # Verify empty tools list is passed
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=messages,
            stream=True,
            tools=[]
        )

    anyio.run(_test)
