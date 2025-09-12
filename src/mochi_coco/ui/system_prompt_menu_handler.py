"""
System prompt menu handler for system prompt-specific operations and interactions.
"""

from typing import List, Optional
from ..services.system_prompt_service import SystemPromptService, SystemPromptInfo
from .user_interaction import UserInteraction


class SystemPromptSelectionContext:
    """Constants for different contexts where system prompt selection can occur."""
    NEW_SESSION = "new_session"          # Creating new session
    FROM_MENU = "from_menu"              # /menu command during chat


class SystemPromptMenuHandler:
    """Handles system prompt-specific operations and interactions."""

    def __init__(self, system_prompt_service: SystemPromptService):
        """
        Initialize the system prompt menu handler.

        Args:
            system_prompt_service: Service for system prompt operations
        """
        self.system_prompt_service = system_prompt_service
        self.user_interaction = UserInteraction()

    def select_system_prompt(self, context: str = SystemPromptSelectionContext.NEW_SESSION) -> Optional[str]:
        """
        Display system prompt selection menu and return the selected system prompt content.

        Args:
            context: Context where system prompt selection is occurring

        Returns:
            Selected system prompt content or None if cancelled/no selection
        """
        # Check if system prompts are available
        if not self.system_prompt_service.has_system_prompts():
            if context == SystemPromptSelectionContext.NEW_SESSION:
                # For new sessions, just continue without system prompt
                return None
            else:
                # For menu context, show message
                self.user_interaction.display_error("No system prompts found in system_prompts/ directory.")
                return None

        # Load available system prompts
        prompts = self._load_available_system_prompts()
        if not prompts:
            return None

        # Display system prompts table
        from .menu_display import MenuDisplay
        menu_display = MenuDisplay()
        menu_display.display_system_prompts_table(prompts)

        # Handle user selection
        return self._handle_system_prompt_selection_loop(prompts, context)

    def _load_available_system_prompts(self) -> Optional[List[SystemPromptInfo]]:
        """
        Load available system prompts from the service.

        Returns:
            List of available system prompts or None if loading failed
        """
        try:
            prompts = self.system_prompt_service.list_system_prompts()
            return prompts
        except Exception as e:
            self.user_interaction.display_error(f"Error loading system prompts: {e}")
            return None

    def _handle_system_prompt_selection_loop(self, prompts: List[SystemPromptInfo], context: str) -> Optional[str]:
        """
        Handle the system prompt selection input loop.

        Args:
            prompts: List of available system prompts
            context: Context where selection is occurring

        Returns:
            Selected system prompt content or None if cancelled
        """
        while True:
            try:
                choice = self.user_interaction.get_user_input("Enter your choice:")

                # Handle quit commands
                if choice.lower() in {'q', 'quit', 'exit'}:
                    if context == SystemPromptSelectionContext.NEW_SESSION:
                        self.user_interaction.display_info("Continuing without system prompt...")
                        return None
                    else:
                        self.user_interaction.display_info("System prompt selection cancelled.")
                        return None

                # Handle "no" for no system prompt
                if choice.lower() in {'no', 'none'}:
                    if context == SystemPromptSelectionContext.NEW_SESSION:
                        self.user_interaction.display_info("Continuing without system prompt...")
                        return None
                    else:
                        self.user_interaction.display_info("System prompt removed.")
                        return ""  # Empty string indicates removal

                # Handle delete commands
                if choice.lower().startswith('/delete'):
                    delete_result = self._handle_delete_command(choice, prompts)
                    if delete_result == "REFRESH":
                        # Refresh prompt list and display
                        new_prompts = self._load_available_system_prompts()
                        if not new_prompts:
                            self.user_interaction.display_info("No system prompts remaining.")
                            return None
                        prompts = new_prompts
                        from .menu_display import MenuDisplay
                        menu_display = MenuDisplay()
                        menu_display.display_system_prompts_table(prompts)
                    continue

                # Handle empty input
                if not choice:
                    continue

                # Handle system prompt selection
                selected_content = self._process_system_prompt_choice(prompts, choice)
                if selected_content is not None:
                    return selected_content
                else:
                    self.user_interaction.display_error("Invalid choice.")
                    continue

            except KeyboardInterrupt:
                self.user_interaction.display_info("Use 'q' to quit system prompt selection.")
                continue

    def _process_system_prompt_choice(self, prompts: List[SystemPromptInfo], choice: str) -> Optional[str]:
        """
        Process the user's system prompt choice.

        Args:
            prompts: List of available system prompts
            choice: User's input choice

        Returns:
            Selected system prompt content, or None for error/invalid choice
        """
        try:
            index = int(choice) - 1

            if 0 <= index < len(prompts):
                selected_prompt = prompts[index]
                content = self.system_prompt_service.load_system_prompt_content(selected_prompt.filename)

                if content:
                    self.user_interaction.display_success(f"Selected system prompt: {selected_prompt.filename}")
                    return content
                else:
                    self.user_interaction.display_error(f"Failed to load system prompt: {selected_prompt.filename}")
                    return None
            else:
                self.user_interaction.display_error(f"Please enter a number between 1 and {len(prompts)}")
                return None

        except ValueError:
            self.user_interaction.display_error("Please enter a valid number")
            return None

    def _handle_delete_command(self, choice: str, prompts: List[SystemPromptInfo]) -> str:
        """
        Handle delete command for system prompts.

        Args:
            choice: User's delete command input
            prompts: List of available prompts

        Returns:
            "REFRESH" if list needs refresh, "CONTINUE" otherwise
        """
        try:
            # Parse delete command: "/delete N"
            parts = choice.split()
            if len(parts) != 2:
                self.user_interaction.display_error("Usage: /delete <number>")
                return "CONTINUE"

            index = int(parts[1]) - 1
            if 0 <= index < len(prompts):
                prompt_to_delete = prompts[index]

                # Confirm deletion
                confirm_msg = f"Delete '{prompt_to_delete.filename}'? (y/N):"
                confirmation = self.user_interaction.get_user_input(confirm_msg)

                if confirmation.lower() in {'y', 'yes'}:
                    if self.system_prompt_service.delete_system_prompt(prompt_to_delete.filename):
                        self.user_interaction.display_success(f"Deleted system prompt: {prompt_to_delete.filename}")
                        return "REFRESH"
                    else:
                        self.user_interaction.display_error(f"Failed to delete: {prompt_to_delete.filename}")
                else:
                    self.user_interaction.display_info("Deletion cancelled.")

                return "CONTINUE"
            else:
                self.user_interaction.display_error(f"Please enter a number between 1 and {len(prompts)}")
                return "CONTINUE"

        except ValueError:
            self.user_interaction.display_error("Invalid delete command. Usage: /delete <number>")
            return "CONTINUE"
        except Exception as e:
            self.user_interaction.display_error(f"Error processing delete command: {e}")
            return "CONTINUE"

    def get_current_system_prompt_info(self, source_file: str) -> Optional[SystemPromptInfo]:
        """
        Get information about currently active system prompt.

        Args:
            source_file: Filename of the current system prompt

        Returns:
            SystemPromptInfo for the current prompt or None if not found
        """
        if not source_file:
            return None

        try:
            prompts = self.system_prompt_service.list_system_prompts()
            for prompt in prompts:
                if prompt.filename == source_file:
                    return prompt
            return None
        except Exception:
            return None
