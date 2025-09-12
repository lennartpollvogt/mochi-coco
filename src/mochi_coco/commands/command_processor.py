"""
Command processor for handling special commands in the chat interface.
"""

from typing import Optional, TYPE_CHECKING
import typer
from datetime import datetime

from ..rendering import RenderingMode
from ..utils import re_render_chat_history

if TYPE_CHECKING:
    from ..chat import ChatSession
    from ..ui import ModelSelector
    from ..services import RendererManager


class CommandResult:
    """Result of command execution."""

    def __init__(self, should_continue: bool = True, should_exit: bool = False,
                 new_session: Optional["ChatSession"] = None, new_model: Optional[str] = None):
        self.should_continue = should_continue
        self.should_exit = should_exit
        self.new_session = new_session
        self.new_model = new_model


class CommandProcessor:
    """Handles processing of special commands in the chat interface."""

    def __init__(self, model_selector: "ModelSelector", renderer_manager: "RendererManager"):
        self.model_selector = model_selector
        self.renderer_manager = renderer_manager

        # Initialize system prompt services
        from ..services import SystemPromptService
        from ..ui import SystemPromptMenuHandler
        self.system_prompt_service = SystemPromptService()
        self.system_prompt_menu_handler = SystemPromptMenuHandler(
            self.system_prompt_service
        )

    def process_command(self, user_input: str, session: "ChatSession", selected_model: str) -> CommandResult:
        """
        Process a user command and return the result.

        Args:
            user_input: The user's input string
            session: Current chat session
            selected_model: Currently selected model name

        Returns:
            CommandResult indicating what action to take
        """
        command = user_input.strip()

        # Exit commands
        if command.lower() in {"/exit", "/quit", "/q"}:
            typer.secho("Goodbye.", fg=typer.colors.YELLOW)
            return CommandResult(should_continue=False, should_exit=True)

        # Menu command
        if command == "/menu":
            return self._handle_menu_command(session)

        # Edit command
        if command == "/edit":
            return self._handle_edit_command(session)

        # Not a recognized command
        return CommandResult(should_continue=False)

    def _handle_models_command(self, session: "ChatSession") -> CommandResult:
        """Handle the /models command."""
        try:
            from ..ui.model_menu_handler import ModelSelectionContext
            new_model = self.model_selector.select_model(context=ModelSelectionContext.FROM_CHAT)
            if new_model:
                session.model = new_model
                session.metadata.model = new_model
                session.save_session()
                typer.secho(f"\n✅ Switched to model: {new_model}\n", fg=typer.colors.GREEN, bold=True)
                return CommandResult(new_model=new_model)
            return CommandResult()
        except Exception as e:
            typer.secho(f"\n❌ Error editing message: {e}", fg=typer.colors.RED)
            return CommandResult()

    def _handle_system_prompt_command(self, session: "ChatSession") -> CommandResult:
        """Handle system prompt changes."""
        try:
            if not self.system_prompt_service.has_system_prompts():
                typer.secho("\n❌ No system prompts found in system_prompts/ directory.", fg=typer.colors.RED)
                return CommandResult()

            # Show current system prompt if exists
            current_file = session.get_current_system_prompt_file()
            if current_file:
                typer.secho(f"\n📝 Current system prompt: {current_file}", fg=typer.colors.BLUE)

            # Show system prompt selection
            from ..ui.system_prompt_menu_handler import SystemPromptSelectionContext
            new_content = self.system_prompt_menu_handler.select_system_prompt(SystemPromptSelectionContext.FROM_MENU)

            if new_content is not None:
                if new_content == "":  # Empty string indicates removal
                    if session.has_system_message():
                        # Remove system message
                        session.messages = [msg for msg in session.messages if msg.role != "system"]
                        session.metadata.message_count = len(session.messages)
                        session.metadata.updated_at = datetime.now().isoformat()
                        session.save_session()
                        typer.secho("\n✅ System prompt removed.\n", fg=typer.colors.GREEN, bold=True)
                    else:
                        typer.secho("\n💡 No system prompt was active.\n", fg=typer.colors.YELLOW)
                else:
                    # Update system prompt
                    session.update_system_message(new_content)
                    typer.secho("\n✅ System prompt updated.\n", fg=typer.colors.GREEN, bold=True)

            return CommandResult()

        except Exception as e:
            typer.secho(f"\n❌ Error changing system prompt: {e}", fg=typer.colors.RED)
            return CommandResult()

    def _handle_markdown_command(self) -> CommandResult:
        """Handle markdown toggle command."""
        try:
            self.renderer_manager.toggle_markdown()
            status = "enabled" if self.renderer_manager.is_markdown_enabled() else "disabled"
            typer.secho(f"\n✅ Markdown rendering {status}.\n", fg=typer.colors.GREEN, bold=True)
            return CommandResult()
        except Exception as e:
            typer.secho(f"\n❌ Error toggling markdown: {e}", fg=typer.colors.RED)
            return CommandResult()

    def _handle_thinking_command(self) -> CommandResult:
        """Handle thinking blocks toggle command."""
        try:
            self.renderer_manager.toggle_thinking()
            status = "enabled" if self.renderer_manager.is_thinking_enabled() else "disabled"
            typer.secho(f"\n✅ Thinking blocks {status}.\n", fg=typer.colors.GREEN, bold=True)
            return CommandResult()
        except Exception as e:
            typer.secho(f"\n❌ Error toggling thinking blocks: {e}", fg=typer.colors.RED)
            return CommandResult()

    def _handle_chats_command(self) -> CommandResult:
        """Handle the /chats command."""
        typer.secho("\n🔄 Switching chat sessions...\n", fg=typer.colors.BLUE, bold=True)
        new_session, new_model, new_markdown_enabled, new_show_thinking = self.model_selector.select_session_or_new()

        if new_session is None and new_model is None:
            # User cancelled - continue with current session
            typer.secho("Returning to current session.\n", fg=typer.colors.YELLOW)
            return CommandResult()

        # Update renderer settings with new preferences
        self.renderer_manager.configure_renderer(new_markdown_enabled, new_show_thinking)

        if new_session:
            # Switched to existing session
            self.model_selector.display_chat_history(new_session)
            typer.secho(f"\n💬 Switched to session {new_session.session_id} with {new_session.metadata.model}",
                       fg=typer.colors.BRIGHT_GREEN)
            result = CommandResult(new_session=new_session, new_model=new_session.metadata.model)
        elif new_model:
            # Created new session with valid model
            from ..chat import ChatSession
            new_session = ChatSession(model=new_model)
            typer.secho(f"\n💬 New chat started with {new_model}", fg=typer.colors.BRIGHT_GREEN)
            typer.secho(f"Session ID: {new_session.session_id}", fg=typer.colors.CYAN)
            result = CommandResult(new_session=new_session, new_model=new_model)
        else:
            # This shouldn't happen, but handle gracefully
            typer.secho("Error: No session or model selected. Returning to current session.", fg=typer.colors.RED)
            return CommandResult()

        # Show updated preferences
        if new_markdown_enabled:
            typer.secho("Markdown rendering is enabled.", fg=typer.colors.CYAN)
            if new_show_thinking:
                typer.secho("Thinking blocks will be displayed.", fg=typer.colors.CYAN)

        return result

    def _handle_markdown_command(self, session: "ChatSession") -> CommandResult:
        """Handle the /markdown command."""
        # Toggle rendering mode
        new_mode = self.renderer_manager.toggle_markdown_mode()

        status = "enabled" if new_mode == RenderingMode.MARKDOWN else "disabled"
        typer.secho(f"\n✅ Markdown rendering {status}", fg=typer.colors.GREEN, bold=True)

        # Re-render chat history with new mode
        re_render_chat_history(session, self.model_selector)
        return CommandResult()

    def _handle_thinking_command(self, session: "ChatSession") -> CommandResult:
        """Handle the /thinking command."""
        if not self.renderer_manager.can_toggle_thinking():
            typer.secho("\n⚠️ Thinking blocks can only be toggled in markdown mode.", fg=typer.colors.YELLOW)
            typer.secho("Enable markdown first with '/markdown' command.\n", fg=typer.colors.YELLOW)
        else:
            # Toggle thinking blocks
            new_thinking_state = self.renderer_manager.toggle_thinking_display()
            status = "shown" if new_thinking_state else "hidden"
            typer.secho(f"\n✅ Thinking blocks will be {status}", fg=typer.colors.GREEN, bold=True)

            # Re-render chat history with new thinking setting
            re_render_chat_history(session, self.model_selector)

        return CommandResult()

    def _handle_edit_command(self, session: "ChatSession") -> CommandResult:
        """Handle the /edit command."""
        from ..ui.user_interaction import UserInteraction

        # Check if there are any user messages to edit
        user_messages = session.get_user_messages_with_indices()
        if not user_messages:
            typer.secho("\n⚠️ No user messages to edit in this session.", fg=typer.colors.YELLOW)
            return CommandResult()

        # Check if session has any messages at all
        if not session.messages:
            typer.secho("\n⚠️ No messages in this session.", fg=typer.colors.YELLOW)
            return CommandResult()

        # Display edit menu
        typer.secho("\n✏️ Edit Message", fg=typer.colors.BLUE, bold=True)
        self.model_selector.menu_display.display_edit_messages_table(session)

        # Get user selection
        user_interaction = UserInteraction()
        selected_index = user_interaction.get_edit_selection(len(user_messages))

        if selected_index is None:
            # User cancelled
            typer.secho("Edit cancelled.", fg=typer.colors.YELLOW)
            return CommandResult()

        # Get the message to edit
        display_num, actual_index, message = user_messages[selected_index - 1]

        typer.secho(f"\nEditing message #{display_num}:", fg=typer.colors.CYAN, bold=True)
        typer.secho("Original message:", fg=typer.colors.YELLOW)
        typer.echo(f"  {message.content}")
        typer.echo()

        # Get edited content
        from ..user_prompt import get_user_input_with_prefill
        typer.secho("Enter your edited message (or press Ctrl+C to cancel):", fg=typer.colors.CYAN)
        try:
            edited_content = get_user_input_with_prefill(prefill_text=message.content)
            if not edited_content.strip():
                typer.secho("Empty message. Edit cancelled.", fg=typer.colors.YELLOW)
                return CommandResult()

            # Check if content actually changed
            if edited_content.strip() == message.content.strip():
                typer.secho("No changes made. Edit cancelled.", fg=typer.colors.YELLOW)
                return CommandResult()

        except (EOFError, KeyboardInterrupt):
            typer.secho("\nEdit cancelled.", fg=typer.colors.YELLOW)
            return CommandResult()

        # Apply the edit
        session.edit_message_and_truncate(actual_index, edited_content)

        # Show confirmation
        typer.secho(f"\nMessage #{display_num} edited successfully!", fg=typer.colors.GREEN, bold=True)
        typer.secho("All messages after this point have been removed.", fg=typer.colors.YELLOW)

        # Re-render chat history to show the changes
        # Re-render chat history to show the changes
        from ..utils import re_render_chat_history
        re_render_chat_history(session, self.model_selector)

        # Automatically continue conversation by getting LLM response
        self._get_llm_response_for_last_message(session)

        return CommandResult()

    def _get_llm_response_for_last_message(self, session: "ChatSession") -> None:
        """Get LLM response for the last user message in the session."""
        if not session.messages or session.messages[-1].role != "user":
            typer.secho("No user message to respond to.", fg=typer.colors.YELLOW)
            return

        try:
            typer.secho("\nContinuing conversation from edited message...", fg=typer.colors.CYAN)
            typer.secho(f"Sending to {session.metadata.model}...\n", fg=typer.colors.BLUE)
            typer.secho("Assistant:", fg=typer.colors.MAGENTA, bold=True)

            # Get current model from session
            current_model = session.metadata.model

            # Get messages for API
            messages = session.get_messages_for_api()

            # Import client from model_selector
            client = self.model_selector.client

            # Use renderer for streaming response
            text_stream = client.chat_stream(current_model, messages)
            final_chunk = self.renderer_manager.renderer.render_streaming_response(text_stream)

            print()  # Extra newline for spacing
            if final_chunk:
                session.add_message(chunk=final_chunk)
                typer.secho("\n✅ Conversation continued successfully!", fg=typer.colors.GREEN)
            else:
                typer.secho("No response received from the model.", fg=typer.colors.RED)

        except Exception as e:
            typer.secho(f"Error getting LLM response: {e}", fg=typer.colors.RED)
            typer.secho("You can continue chatting normally.", fg=typer.colors.YELLOW)

    def _handle_menu_command(self, session: "ChatSession") -> CommandResult:
        """Handle the /menu command by displaying menu options and processing selection."""
        from ..ui.user_interaction import UserInteraction

        while True:
            # Check if system prompts are available
            has_system_prompts = self.system_prompt_service.has_system_prompts()

            # Display the menu
            self.model_selector.menu_display.display_command_menu(has_system_prompts)

            # Get user selection
            user_interaction = UserInteraction()
            choice = user_interaction.get_user_input()

            # Handle quit
            if choice.lower() in {'q', 'quit', 'exit'}:
                typer.secho("Returning to chat.", fg=typer.colors.YELLOW)
                return CommandResult()

            # Process menu selection
            if choice == "1":
                # Handle chats command
                result = self._handle_chats_command()
                if result.should_exit or (result.new_session or result.new_model):
                    return result
                # If user cancelled, continue menu loop
                continue
            elif choice == "2":
                # Handle models command
                result = self._handle_models_command(session)
                if result.new_model:
                    return result
                # If user cancelled, continue menu loop
                continue
            elif choice == "3":
                # Handle markdown command
                result = self._handle_markdown_command(session)
                return result  # Always return after markdown toggle
            elif choice == "4":
                # Handle thinking command
                result = self._handle_thinking_command(session)
                return result  # Always return after thinking toggle
            elif choice == "5" and has_system_prompts:
                # Handle system prompt command
                result = self._handle_system_prompt_command(session)
                return result  # Always return after system prompt change
            else:
                max_option = 5 if has_system_prompts else 4
                typer.secho(f"Please enter 1-{max_option} or 'q'", fg=typer.colors.RED)
                continue
