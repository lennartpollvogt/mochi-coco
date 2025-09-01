"""
Model menu handler for model-specific operations and interactions.
"""

from typing import List, Optional
from ..ollama.client import OllamaClient, ModelInfo
from .menu_display import MenuDisplay
from .user_interaction import UserInteraction


class ModelMenuHandler:
    """Handles model-specific operations and interactions."""

    def __init__(self, client: OllamaClient, menu_display: MenuDisplay):
        """
        Initialize the model menu handler.

        Args:
            client: Ollama client for model operations
            menu_display: Display handler for showing UI elements
        """
        self.client = client
        self.menu_display = menu_display

    def select_model(self) -> Optional[str]:
        """
        Display model selection menu and return the selected model name.

        Returns:
            Selected model name or None if cancelled/failed
        """
        self.menu_display.display_model_selection_header()

        # Load available models
        models = self._load_available_models()
        if not models:
            return None

        # Validate models have required data
        if not self._validate_model_availability(models):
            UserInteraction.display_error("No valid models available. Please install some models first.")
            return None

        # Display models table
        self.menu_display.display_models_table(models, self.client)

        # Handle user selection
        return self._handle_model_selection_loop(models)

    def _load_available_models(self) -> Optional[List[ModelInfo]]:
        """
        Load available models from the client.

        Returns:
            List of available models or None if loading failed
        """
        try:
            models = self.client.list_models()
            return models
        except Exception as e:
            UserInteraction.display_error(f"Error loading models: {e}")
            return None

    def _validate_model_availability(self, models: List[ModelInfo]) -> bool:
        """
        Validate that models are available and have required data.

        Args:
            models: List of models to validate

        Returns:
            True if models are valid, False otherwise
        """
        if not models:
            return False

        # Check if at least one model has a valid name
        valid_models = [model for model in models if model.name]
        return len(valid_models) > 0

    def _handle_model_selection_loop(self, models: List[ModelInfo]) -> Optional[str]:
        """
        Handle the model selection input loop.

        Args:
            models: List of available models

        Returns:
            Selected model name or None if cancelled
        """
        while True:
            try:
                self.menu_display.display_model_selection_prompt(len(models))
                choice = UserInteraction.get_user_input("Enter your choice:")
                # Handle quit commands
                if choice.lower() in {'q', 'quit', 'exit'}:
                    UserInteraction.display_success('Model selection cancelled')
                    return None

                # Handle empty input
                if not choice:
                    continue

                # Handle model selection
                selected_model = self._process_model_choice(models, choice)
                if selected_model is not None:
                    return selected_model
                else:
                    UserInteraction.display_error("Invalid model choice.")
                    continue

            except KeyboardInterrupt:
                UserInteraction.display_info("Use 'q' to quit model selection.")
                continue

    def _process_model_choice(self, models: List[ModelInfo], choice: str) -> Optional[str]:
        """
        Process the user's model choice.

        Args:
            models: List of available models
            choice: User's input choice

        Returns:
            Selected model name, empty string to continue loop, or None for error
        """
        try:
            index = int(choice) - 1

            if 0 <= index < len(models):
                selected_model = models[index].name
                if selected_model:
                    self.menu_display.display_model_selected(selected_model)
                    return selected_model
                else:
                    UserInteraction.display_error("Selected model has no name")
                    return None  # Continue loop
            else:
                UserInteraction.display_error(f"Please enter a number between 1 and {len(models)}")
                return None  # Continue loop

        except ValueError:
            UserInteraction.display_error("Please enter a valid number")
            return None # Continue loop

    def check_model_availability(self, model_name: str) -> bool:
        """
        Check if a specific model is still available.

        Args:
            model_name: Name of the model to check

        Returns:
            True if model is available, False otherwise
        """
        try:
            available_models = self.client.list_models()
            model_names = [model.name for model in available_models if model.name]
            return model_name in model_names
        except Exception:
            return False

    def get_available_model_names(self) -> List[str]:
        """
        Get list of available model names.

        Returns:
            List of model names, empty list if none available
        """
        try:
            models = self.client.list_models()
            return [model.name for model in models if model.name]
        except Exception:
            return []

    def handle_unavailable_model(self, unavailable_model: str) -> Optional[str]:
        """
        Handle the case when a session's model is no longer available.

        Args:
            unavailable_model: Name of the unavailable model

        Returns:
            New selected model name or None if cancelled
        """
        UserInteraction.display_warning(f"Model '{unavailable_model}' is no longer available.")
        UserInteraction.display_info("Please select a new model:")

        return self.select_model()
