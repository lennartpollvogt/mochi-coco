from typing import Iterator, List, Dict, Optional, Any
from dataclasses import dataclass

from ollama import Client, list as ollama_list, ListResponse


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ModelInfo:
    name: str
    size_mb: float
    format: Optional[str] = None
    family: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None


class OllamaClient:
    def __init__(self, host: Optional[str] = None):
        self.client = Client(host=host) if host else Client()

    def list_models(self) -> List[ModelInfo]:
        """List all available models."""
        try:
            response: ListResponse = ollama_list()
            models = []

            for model in response.models:
                size_mb = model.size / 1024 / 1024 if model.size else 0

                model_info = ModelInfo(
                    name=model.model,
                    size_mb=size_mb,
                    format=model.details.format if model.details else None,
                    family=model.details.family if model.details else None,
                    parameter_size=model.details.parameter_size if model.details else None,
                    quantization_level=model.details.quantization_level if model.details else None,
                )
                models.append(model_info)

            return models
        except Exception as e:
            raise Exception(f"Failed to list models: {e}")

    def chat_stream(self, model: str, messages: List[Dict[str, str]]) -> Iterator[str]:
        """Stream chat responses from the model."""
        try:
            response_stream = self.client.chat(
                model=model,
                messages=messages,
                stream=True
            )

            for chunk in response_stream:
                if chunk.message and chunk.message.content:
                    yield chunk.message.content
        except Exception as e:
            raise Exception(f"Chat failed: {e}")
