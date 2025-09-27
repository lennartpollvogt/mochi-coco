from typing import Iterator, List, Optional, Sequence, Mapping, Any, Union, Callable
from dataclasses import dataclass

from ollama import (
    Client,
    list as ollama_list,
    ListResponse,
    ChatResponse,
    Message,
    ShowResponse,
    Tool,
)


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


class OllamaClient:
    def __init__(self, host: Optional[str] = None):
        self.client = Client(host=host) if host else Client()

    def list_models(self) -> List[ModelInfo]:
        """List all available models that support completion."""
        try:
            response: ListResponse = ollama_list()
            models = []

            for model in response.models:
                if not model.model:
                    continue

                # Get detailed model information including capabilities
                try:
                    model_details = self.show_model_details(model.model)
                    capabilities = model_details.model_dump().get("capabilities", [])

                    # Only include models that support completion
                    if "completion" not in capabilities:
                        continue

                    # Extract context length from modelinfo
                    context_length = None
                    model_info_dict = model_details.model_dump().get("modelinfo", {})
                    family = model.details.family if model.details else None
                    if family and f"{family}.context_length" in model_info_dict:
                        context_length = model_info_dict[f"{family}.context_length"]

                except Exception:
                    # If we can't get model details, skip this model
                    continue

                size_mb = model.size / 1024 / 1024 if model.size else 0

                model_info = ModelInfo(
                    name=model.model,
                    size_mb=size_mb,
                    format=model.details.format if model.details else None,
                    family=model.details.family if model.details else None,
                    parameter_size=model.details.parameter_size
                    if model.details
                    else None,
                    quantization_level=model.details.quantization_level
                    if model.details
                    else None,
                    capabilities=capabilities,
                    context_length=context_length,
                )
                models.append(model_info)

            return models
        except Exception as e:
            raise Exception(f"Failed to list models: {e}")

    def show_model_details(self, model_name: str) -> ShowResponse:
        """Get model details with method 'show'."""
        try:
            model_details = self.client.show(model=model_name)
            return model_details
        except Exception as e:
            raise Exception(f"Failed to show model details: {e}")

    def chat_stream(
        self,
        model: str,
        messages: Sequence[Mapping[str, Any] | Message],
        tools: Optional[Sequence[Union[Tool, Callable]]] = None,
        think: Optional[bool] = None,
    ) -> Iterator[ChatResponse]:
        """
        Stream chat responses from the model with optional tool support.

        Args:
            model: Model name to use for generation
            messages: Sequence of chat messages
            tools: Optional list of Tool objects or callable functions
            think: Enable thinking mode for supported models

        Yields:
            ChatResponse chunks during streaming
        """
        try:
            # Build kwargs dynamically to maintain backward compatibility
            kwargs = {"model": model, "messages": messages, "stream": True}

            # Only add optional parameters if provided
            if tools is not None:
                kwargs["tools"] = tools
            if think is not None:
                kwargs["think"] = think

            response_stream: Iterator[ChatResponse] = self.client.chat(**kwargs)

            for chunk in response_stream:
                if chunk.message and chunk.message.content:
                    # For streaming chunks, context_window is None
                    # yield ChatResponse(message=chunk.message)
                    yield chunk
                    # yield chunk.message.content, None
                elif (
                    hasattr(chunk, "done")
                    and chunk.done
                    and hasattr(chunk, "eval_count")
                ):
                    # Final chunk with metadata - yield empty content with context window
                    # yield ChatResponse(message=chunk.message, eval_count=chunk.eval_count, prompt_eval_count=chunk.prompt_eval_count)
                    yield chunk
                    # yield "", chunk.prompt_eval_count
                elif hasattr(chunk.message, "tool_calls") and chunk.message.tool_calls:
                    # Tool call chunk - yield even if content is empty
                    yield chunk
        except Exception as e:
            raise Exception(f"Chat failed: {e}")

    def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, Any] | Message],
        tools: Optional[Sequence[Union[Tool, Callable]]] = None,
        think: Optional[bool] = None,
    ) -> ChatResponse:
        """
        Non-streaming chat with optional tool support.

        Args:
            model: Model name to use for generation
            messages: Sequence of chat messages
            tools: Optional list of Tool objects or callable functions
            think: Enable thinking mode for supported models

        Returns:
            Complete ChatResponse
        """
        try:
            kwargs = {"model": model, "messages": messages, "stream": False}

            if tools is not None:
                kwargs["tools"] = tools
            if think is not None:
                kwargs["think"] = think

            return self.client.chat(**kwargs)

        except Exception as e:
            raise Exception(f"Chat failed: {e}")
