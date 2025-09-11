"""
Comprehensive tests for OllamaClient class.

Tests cover model listing, model details, streaming chat functionality,
and robust error handling for external API integration.
"""

import pytest
from unittest.mock import Mock, patch

from mochi_coco.ollama.client import OllamaClient, ModelInfo


class TestOllamaClient:
    """Test suite for OllamaClient functionality."""

    @pytest.fixture
    def client(self):
        """Create an OllamaClient instance for testing."""
        return OllamaClient()

    @pytest.fixture
    def client_with_host(self):
        """Create an OllamaClient instance with custom host."""
        return OllamaClient(host="http://test-host:11434")

    @pytest.fixture
    def mock_ollama_list_response(self):
        """Create a mock response for ollama.list()."""
        mock_response = Mock()
        mock_response.models = []

        # Create mock model 1
        mock_model1 = Mock()
        mock_model1.model = "llama3.2:latest"
        mock_model1.size = 2048 * 1024 * 1024  # 2GB in bytes
        mock_model1.details = Mock()
        mock_model1.details.format = "gguf"
        mock_model1.details.family = "llama"
        mock_model1.details.parameter_size = "3B"
        mock_model1.details.quantization_level = "Q4_0"

        # Create mock model 2 with minimal details
        mock_model2 = Mock()
        mock_model2.model = "phi3:mini"
        mock_model2.size = 1024 * 1024 * 1024  # 1GB in bytes
        mock_model2.details = None  # Test handling of missing details

        mock_response.models = [mock_model1, mock_model2]
        return mock_response

    @pytest.fixture
    def mock_show_response(self):
        """Create a mock response for client.show()."""
        mock_response = Mock()
        mock_response.model = "test-model"
        mock_response.details = Mock()
        mock_response.details.format = "gguf"
        mock_response.details.family = "llama"
        return mock_response

    def test_client_initialization_default_host(self):
        """Test client initialization with default host."""
        with patch('mochi_coco.ollama.client.Client') as mock_client_class:
            # Create OllamaClient instance within the patched context
            OllamaClient()

            # Should create Client without host parameter
            mock_client_class.assert_called_once_with()

    def test_client_initialization_custom_host(self):
        """Test client initialization with custom host."""
        custom_host = "http://localhost:8080"

        with patch('mochi_coco.ollama.client.Client') as mock_client_class:
            # Create OllamaClient instance with custom host within the patched context
            OllamaClient(host=custom_host)

            # Should create Client with host parameter
            mock_client_class.assert_called_once_with(host=custom_host)

    @patch('mochi_coco.ollama.client.ollama_list')
    def test_list_models_success(self, mock_list, client, mock_ollama_list_response):
        """Test successful model listing and ModelInfo creation."""
        mock_list.return_value = mock_ollama_list_response

        # Mock show_model_details for capability checking
        def mock_show_details(model_name):
            mock_response = Mock()
            if model_name == "llama3.2:latest":
                mock_response.model_dump.return_value = {
                    'capabilities': ['completion', 'tools'],
                    'modelinfo': {'llama.context_length': 131072}
                }
            elif model_name == "phi3:mini":
                mock_response.model_dump.return_value = {
                    'capabilities': ['completion'],
                    'modelinfo': {}
                }
            return mock_response

        client.show_model_details = Mock(side_effect=mock_show_details)

        models = client.list_models()

        assert len(models) == 2

        # Test first model with full details
        model1 = models[0]
        assert isinstance(model1, ModelInfo)
        assert model1.name == "llama3.2:latest"
        assert model1.size_mb == 2048.0  # 2GB converted to MB
        assert model1.format == "gguf"
        assert model1.family == "llama"
        assert model1.parameter_size == "3B"
        assert model1.quantization_level == "Q4_0"
        assert model1.capabilities == ['completion', 'tools']
        assert model1.context_length == 131072

        # Test second model with missing details
        model2 = models[1]
        assert model2.name == "phi3:mini"
        assert model2.size_mb == 1024.0
        assert model2.format is None
        assert model2.family is None
        assert model2.parameter_size is None
        assert model2.quantization_level is None
        assert model2.capabilities == ['completion']
        assert model2.context_length is None

    @patch('mochi_coco.ollama.client.ollama_list')
    def test_list_models_empty_response(self, mock_list, client):
        """Test handling of empty model list."""
        mock_response = Mock()
        mock_response.models = []
        mock_list.return_value = mock_response

        models = client.list_models()

        assert models == []

    @patch('mochi_coco.ollama.client.ollama_list')
    def test_list_models_zero_size_handling(self, mock_list, client):
        """Test handling of models with zero or None size."""
        mock_response = Mock()
        mock_model = Mock()
        mock_model.model = "test-model"
        mock_model.size = None
        mock_model.details = None
        mock_response.models = [mock_model]
        mock_list.return_value = mock_response

        # Mock show_model_details to return completion capability
        def mock_show_details(model_name):
            mock_response = Mock()
            mock_response.model_dump.return_value = {
                'capabilities': ['completion'],
                'modelinfo': {}
            }
            return mock_response

        client.show_model_details = Mock(side_effect=mock_show_details)

        models = client.list_models()

        assert len(models) == 1
        assert models[0].size_mb == 0
        assert models[0].capabilities == ['completion']

    @patch('mochi_coco.ollama.client.ollama_list')
    def test_list_models_filters_non_completion_models(self, mock_list, client):
        """Test that models without completion capability are filtered out."""
        mock_response = Mock()

        # Create mock model with only embedding capability (should be filtered out)
        mock_model1 = Mock()
        mock_model1.model = "embed-model"
        mock_model1.size = 500 * 1024 * 1024
        mock_model1.details = Mock()
        mock_model1.details.family = "nomic-bert"

        # Create mock model with completion capability (should be included)
        mock_model2 = Mock()
        mock_model2.model = "completion-model"
        mock_model2.size = 1000 * 1024 * 1024
        mock_model2.details = Mock()
        mock_model2.details.family = "llama"

        mock_response.models = [mock_model1, mock_model2]
        mock_list.return_value = mock_response

        # Mock show_model_details to return different capabilities
        def mock_show_details(model_name):
            mock_response = Mock()
            if model_name == "embed-model":
                mock_response.model_dump.return_value = {
                    'capabilities': ['embedding'],  # No completion capability
                    'modelinfo': {}
                }
            elif model_name == "completion-model":
                mock_response.model_dump.return_value = {
                    'capabilities': ['completion'],
                    'modelinfo': {'llama.context_length': 4096}
                }
            return mock_response

        client.show_model_details = Mock(side_effect=mock_show_details)

        models = client.list_models()

        # Only the completion model should be included
        assert len(models) == 1
        assert models[0].name == "completion-model"
        assert models[0].capabilities == ['completion']

    @patch('mochi_coco.ollama.client.ollama_list')
    def test_list_models_show_details_failure(self, mock_list, client):
        """Test that models are skipped when show_model_details fails."""
        mock_response = Mock()

        # Create mock models
        mock_model1 = Mock()
        mock_model1.model = "working-model"
        mock_model1.size = 1000 * 1024 * 1024
        mock_model1.details = Mock()
        mock_model1.details.family = "llama"

        mock_model2 = Mock()
        mock_model2.model = "broken-model"
        mock_model2.size = 500 * 1024 * 1024
        mock_model2.details = Mock()
        mock_model2.details.family = "test"

        mock_response.models = [mock_model1, mock_model2]
        mock_list.return_value = mock_response

        # Mock show_model_details to fail for one model
        def mock_show_details(model_name):
            if model_name == "working-model":
                mock_response = Mock()
                mock_response.model_dump.return_value = {
                    'capabilities': ['completion'],
                    'modelinfo': {'llama.context_length': 4096}
                }
                return mock_response
            elif model_name == "broken-model":
                raise Exception("Failed to get model details")

        client.show_model_details = Mock(side_effect=mock_show_details)

        models = client.list_models()

        # Only the working model should be included
        assert len(models) == 1
        assert models[0].name == "working-model"

    @patch('mochi_coco.ollama.client.ollama_list')
    def test_list_models_api_error(self, mock_list, client):
        """Test handling of API errors during model listing."""
        mock_list.side_effect = ConnectionError("Failed to connect to Ollama")

        with pytest.raises(Exception) as exc_info:
            client.list_models()

        assert "Failed to list models" in str(exc_info.value)
        assert "Failed to connect to Ollama" in str(exc_info.value)

    @patch('mochi_coco.ollama.client.ollama_list')
    def test_list_models_generic_error(self, mock_list, client):
        """Test handling of generic errors during model listing."""
        mock_list.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception) as exc_info:
            client.list_models()

        assert "Failed to list models: Unexpected error" in str(exc_info.value)

    def test_show_model_details_success(self, client, mock_show_response):
        """Test successful model details retrieval."""
        with patch.object(client.client, 'show', return_value=mock_show_response):
            details = client.show_model_details("test-model")

            assert details == mock_show_response
            client.client.show.assert_called_once_with(model="test-model")

    def test_show_model_details_model_not_found(self, client):
        """Test handling of model not found error."""
        with patch.object(client.client, 'show', side_effect=Exception("Model not found")):
            with pytest.raises(Exception) as exc_info:
                client.show_model_details("nonexistent-model")

            assert "Failed to show model details" in str(exc_info.value)
            assert "Model not found" in str(exc_info.value)

    def test_show_model_details_connection_error(self, client):
        """Test handling of connection errors during model details retrieval."""
        with patch.object(client.client, 'show', side_effect=ConnectionError("Connection refused")):
            with pytest.raises(Exception) as exc_info:
                client.show_model_details("test-model")

            assert "Failed to show model details" in str(exc_info.value)
            assert "Connection refused" in str(exc_info.value)

    def test_chat_stream_success(self, client):
        """Test successful streaming chat response."""
        # Create mock streaming response
        def mock_chat_generator():
            # First chunk with content
            chunk1 = Mock()
            chunk1.message = Mock()
            chunk1.message.content = "Hello"
            yield chunk1

            # Second chunk with content
            chunk2 = Mock()
            chunk2.message = Mock()
            chunk2.message.content = " there!"
            yield chunk2

            # Final chunk with metadata
            final_chunk = Mock()
            final_chunk.message = Mock()
            final_chunk.message.content = ""
            final_chunk.done = True
            final_chunk.eval_count = 50
            final_chunk.prompt_eval_count = 25
            yield final_chunk

        with patch.object(client.client, 'chat', return_value=mock_chat_generator()):
            messages = [{"role": "user", "content": "Hello"}]

            chunks = list(client.chat_stream("test-model", messages))

            assert len(chunks) == 3
            assert chunks[0].message.content == "Hello"
            assert chunks[1].message.content == " there!"
            assert chunks[2].done is True
            assert chunks[2].eval_count == 50
            assert chunks[2].prompt_eval_count == 25

            # Verify client.chat was called with correct parameters
            client.client.chat.assert_called_once_with(
                model="test-model",
                messages=messages,
                stream=True
            )

    def test_chat_stream_empty_response(self, client):
        """Test handling of empty streaming response."""
        def empty_generator():
            return iter([])

        with patch.object(client.client, 'chat', return_value=empty_generator()):
            messages = [{"role": "user", "content": "Hello"}]

            chunks = list(client.chat_stream("test-model", messages))

            assert chunks == []

    def test_chat_stream_content_only_chunks(self, client):
        """Test streaming response with only content chunks (no final metadata)."""
        def content_only_generator():
            chunk = Mock()
            chunk.message = Mock()
            chunk.message.content = "Response"
            yield chunk

        with patch.object(client.client, 'chat', return_value=content_only_generator()):
            messages = [{"role": "user", "content": "Hello"}]

            chunks = list(client.chat_stream("test-model", messages))

            assert len(chunks) == 1
            assert chunks[0].message.content == "Response"

    def test_chat_stream_api_error(self, client):
        """Test handling of API errors during streaming."""
        with patch.object(client.client, 'chat', side_effect=ConnectionError("Network error")):
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(Exception) as exc_info:
                list(client.chat_stream("test-model", messages))

            assert "Chat failed" in str(exc_info.value)
            assert "Network error" in str(exc_info.value)

    def test_chat_stream_generic_error(self, client):
        """Test handling of generic errors during streaming."""
        with patch.object(client.client, 'chat', side_effect=Exception("Unexpected error")):
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(Exception) as exc_info:
                list(client.chat_stream("test-model", messages))

            assert "Chat failed: Unexpected error" in str(exc_info.value)

    def test_chat_stream_with_different_message_types(self, client):
        """Test chat streaming with different message input types."""
        def mock_chat_generator():
            chunk = Mock()
            chunk.message = Mock()
            chunk.message.content = "Response"
            yield chunk

        with patch.object(client.client, 'chat', return_value=mock_chat_generator()) as mock_chat:
            # Test with dict messages
            dict_messages = [{"role": "user", "content": "Hello"}]
            list(client.chat_stream("test-model", dict_messages))

            # Test with Message objects (mock)
            mock_message = Mock()
            message_objects = [mock_message]
            list(client.chat_stream("test-model", message_objects))

            # Verify both calls were made
            assert mock_chat.call_count == 2

    def test_chat_stream_chunk_without_content(self, client):
        """Test handling of chunks without content."""
        def mock_chat_generator():
            # Chunk with no content
            chunk1 = Mock()
            chunk1.message = Mock()
            chunk1.message.content = ""
            yield chunk1

            # Chunk with None message
            chunk2 = Mock()
            chunk2.message = None
            yield chunk2

            # Normal chunk
            chunk3 = Mock()
            chunk3.message = Mock()
            chunk3.message.content = "Hello"
            yield chunk3

        with patch.object(client.client, 'chat', return_value=mock_chat_generator()):
            messages = [{"role": "user", "content": "Hello"}]

            chunks = list(client.chat_stream("test-model", messages))

            # Should still yield all chunks, including those without content
            assert len(chunks) == 3

    @pytest.mark.integration
    def test_model_info_dataclass_structure(self):
        """Test ModelInfo dataclass structure and defaults."""
        # Test minimal ModelInfo
        model = ModelInfo(name="test-model", size_mb=100.0)

        assert model.name == "test-model"
        assert model.size_mb == 100.0
        assert model.format is None
        assert model.family is None
        assert model.parameter_size is None
        assert model.quantization_level is None

        # Test full ModelInfo
        full_model = ModelInfo(
            name="full-model",
            size_mb=500.0,
            format="gguf",
            family="llama",
            parameter_size="7B",
            quantization_level="Q4_0"
        )

        assert full_model.name == "full-model"
        assert full_model.format == "gguf"
        assert full_model.family == "llama"
        assert full_model.parameter_size == "7B"
        assert full_model.quantization_level == "Q4_0"

    def test_error_message_preservation(self, client):
        """Test that original error messages are preserved in exceptions."""
        original_error = "Original detailed error message"

        # Test list_models error preservation
        with patch('mochi_coco.ollama.client.ollama_list', side_effect=Exception(original_error)):
            with pytest.raises(Exception) as exc_info:
                client.list_models()
            assert original_error in str(exc_info.value)

        # Test show_model_details error preservation
        with patch.object(client.client, 'show', side_effect=Exception(original_error)):
            with pytest.raises(Exception) as exc_info:
                client.show_model_details("test-model")
            assert original_error in str(exc_info.value)

        # Test chat_stream error preservation
        with patch.object(client.client, 'chat', side_effect=Exception(original_error)):
            with pytest.raises(Exception) as exc_info:
                list(client.chat_stream("test-model", []))
            assert original_error in str(exc_info.value)
