from typing import AsyncIterator, List, Optional, Sequence, Mapping, Any, Union, Callable
from dataclasses import dataclass
from pydantic import BaseModel
import logging

from ollama import AsyncClient, ListResponse, ChatResponse, Message, ShowResponse, Tool
from ollama_instructor import OllamaInstructorAsync

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ModelInfo:
    name: str | None
    size_mb: float
    format: Optional[str] = None
    family: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None
    capabilities: Optional[List[str]] = None
    context_length: Optional[int] = None

class AsyncOllamaClient:
    def __init__(self, host: Optional[str] = None):
        self.client = AsyncClient(host=host) if host else AsyncClient()

    async def list_models(self) -> List[ModelInfo]:
        """List all available models that support completion asynchronously."""
        try:
            # Note: ollama_list() is still synchronous, so we'll use the client's list method
            response: ListResponse = await self.client.list()
            models = []

            for model in response.models:
                if not model.model:
                    continue

                # Get detailed model information including capabilities
                try:
                    model_details = await self.show_model_details(model.model)
                    capabilities = model_details.model_dump().get('capabilities', [])

                    # Only include models that support completion
                    if 'completion' not in capabilities:
                        continue

                    # Extract context length from modelinfo
                    context_length = None
                    model_info_dict = model_details.model_dump().get('modelinfo', {})
                    family = model.details.family if model.details else None
                    if family and f'{family}.context_length' in model_info_dict:
                        context_length = model_info_dict[f'{family}.context_length']

                except Exception:
                    # If we can't get model details, skip this model
                    continue

                size_mb = model.size / 1024 / 1024 if model.size else 0

                model_info = ModelInfo(
                    name=model.model,
                    size_mb=size_mb,
                    format=model.details.format if model.details else None,
                    family=model.details.family if model.details else None,
                    parameter_size=model.details.parameter_size if model.details else None,
                    quantization_level=model.details.quantization_level if model.details else None,
                    capabilities=capabilities,
                    context_length=context_length,
                )
                models.append(model_info)

            return models
        except Exception as e:
            raise Exception(f"Failed to list models: {e}")

    async def show_model_details(self, model_name: str) -> ShowResponse:
        """Get model details with method 'show' asynchronously."""
        try:
            model_details = await self.client.show(
                model=model_name
            )
            return model_details
        except Exception as e:
            raise Exception(f"Failed to show model details: {e}")

    async def chat_stream(self, model: str, messages: Sequence[Mapping[str, Any] | Message],
                          tools: Optional[Sequence[Union[Tool, Callable]]] = None,
                          think: Optional[bool] = None) -> AsyncIterator[ChatResponse]:
        """
        Async stream chat responses with optional tool support.

        Args:
            model: Model name to use for generation
            messages: Sequence of chat messages
            tools: Optional list of Tool objects or callable functions
            think: Enable thinking mode for supported models

        Yields:
            ChatResponse chunks during streaming
        """
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "stream": True
            }

            if tools is not None:
                kwargs["tools"] = tools
            if think is not None:
                kwargs["think"] = think

            response_stream = await self.client.chat(**kwargs)

            async for chunk in response_stream:
                if chunk.message and chunk.message.content:
                    yield chunk
                elif hasattr(chunk, 'done') and chunk.done and hasattr(chunk, 'eval_count'):
                    yield chunk
        except Exception as e:
            logger.error(f"Async chat failed: {e}")
            raise

    async def chat_single(self, model: str, messages: Sequence[Mapping[str, Any] | Message],
                          tools: Optional[Sequence[Union[Tool, Callable]]] = None,
                          think: Optional[bool] = None) -> ChatResponse:
        """
        Get a single (non-streaming) chat response from the model asynchronously.

        Args:
            model: Model name to use for generation
            messages: Sequence of chat messages
            tools: Optional list of Tool objects or callable functions
            think: Enable thinking mode for supported models

        Returns:
            Complete ChatResponse
        """
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "stream": False,
                "format": None
            }

            if tools is not None:
                kwargs["tools"] = tools
            if think is not None:
                kwargs["think"] = think

            response = await self.client.chat(**kwargs)
            return response
        except Exception as e:
            logger.error(f"Async chat failed: {e}")
            raise

    async def chat(self, model: str, messages: Sequence[Mapping[str, Any] | Message],
                   tools: Optional[Sequence[Union[Tool, Callable]]] = None,
                   think: Optional[bool] = None) -> ChatResponse:
        """
        Async non-streaming chat with optional tool support.

        Args:
            model: Model name to use for generation
            messages: Sequence of chat messages
            tools: Optional list of Tool objects or callable functions
            think: Enable thinking mode for supported models

        Returns:
            Complete ChatResponse
        """
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "stream": False
            }

            if tools is not None:
                kwargs["tools"] = tools
            if think is not None:
                kwargs["think"] = think

            return await self.client.chat(**kwargs)

        except Exception as e:
            logger.error(f"Async chat failed: {e}")
            raise

class AsyncInstructorOllamaClient:
    def __init__(self, host: Optional[str] = None):
        self.client = OllamaInstructorAsync(host=host, log_level="DEBUG") if host else OllamaInstructorAsync()

    async def structured_response(self, model: str, messages: Sequence[Mapping[str, Any] | Message], format: type[BaseModel]) -> ChatResponse:
        """
        Get a structured response from the model asynchronously.
        """
        system_prompt = {
            "role": "system",
            "content": f"Make sure to answer in a json format. Here is the json schema: {str(format.model_json_schema())}"
        }
        messages = [system_prompt] + list(messages)
        #print(messages)
        try:
            response = await self.client.chat_completion(
                model=model, #"llama3.2:latest",
                messages=messages,
                format=format,
                options={"num_ctx": 131072}
            )
            return response
        except Exception as e:
            raise Exception(f"Structured response failed: {e}")
