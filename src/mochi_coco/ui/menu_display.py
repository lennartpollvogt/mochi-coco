"""
Menu display utilities using Rich for consistent and beautiful formatting.
"""

from typing import List, Optional
import json
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED, HEAVY
from rich.align import Align
from rich.syntax import Syntax

from ..ollama import OllamaClient, ModelInfo
from ..chat import ChatSession
from ..rendering import MarkdownRenderer
from ..services.system_prompt_service import SystemPromptInfo


class MenuDisplay:
    """Handles all table formatting and display logic using Rich for consistent styling."""

    def __init__(self, renderer: Optional[MarkdownRenderer] = None):
        """
        Initialize the display handler.

        Args:
            renderer: Optional markdown renderer for chat history display
        """
        self.renderer = renderer
        self.console = Console()

        # Define consistent color scheme
        self.colors = {
            "primary": "bright_magenta",
            "secondary": "bright_cyan",
            "success": "bright_green",
            "warning": "bright_yellow",
            "error": "bright_red",
            "info": "bright_blue",
            "muted": "bright_black",
        }

    def display_models_table(
        self, models: List[ModelInfo], client: OllamaClient
    ) -> None:
        """Display available models in a Rich table format with integrated options and attention message."""
        if not models:
            error_panel = Panel(
                "❌ No models found!", style=self.colors["error"], box=ROUNDED
            )
            self.console.print(error_panel)
            return

        # Create the models table
        table = Table(
            box=ROUNDED, show_header=True, header_style=self.colors["secondary"]
        )
        table.add_column("#", style=self.colors["secondary"], width=3)
        table.add_column("Model Name", style="bold white", min_width=25)
        table.add_column(
            "Size (MB)", style=self.colors["info"], justify="right", width=12
        )
        table.add_column("Family", style=self.colors["warning"], width=15)
        table.add_column(
            "Max. Cxt", style=self.colors["success"], justify="right", width=8
        )
        table.add_column(
            "Tools", style=self.colors["primary"], justify="center", width=5
        )

        # Add model rows
        for i, model in enumerate(models, 1):
            size_str = f"{model.size_mb:.1f}" if model.size_mb else "N/A"
            family_str = model.family or "N/A"
            context_str = str(model.context_length) if model.context_length else "N/A"

            # Check if model has tools capability
            tools_str = (
                "Yes" if model.capabilities and "tools" in model.capabilities else "No"
            )

            table.add_row(
                str(i),
                model.name or "Unknown",
                size_str,
                family_str,
                context_str,
                tools_str,
            )

        # Create model selection options
        model_count = len(models)
        options_text = Text()
        options_text.append("\n💡 Options:\n", style="bold bright_yellow")
        options_text.append(f"• 🔢 Select model (1-{model_count})\n", style="white")
        options_text.append("• 👋 Type 'q' to quit\n", style="white")

        # Add attention notice
        options_text.append("\n⚠️ ATTENTION: ", style="bold bright_red")
        options_text.append(
            "Max. Cxt. is only supported context length not set.\n", style="yellow"
        )
        options_text.append("💡 ", style="bright_blue")
        options_text.append(
            "Open Ollama application to set default context length!",
            style="bright_blue",
        )

        # Combine table, options, and attention message
        from rich.console import Group

        combined_content = Group(table, options_text)

        # Wrap in panel
        models_panel = Panel(
            combined_content,
            title="🤖 Available Models",
            title_align="left",
            style=self.colors["primary"],
            box=ROUNDED,
        )
        self.console.print(models_panel)

    def display_sessions_table(self, sessions: List[ChatSession]) -> None:
        """Display available sessions in a Rich table format with integrated menu options."""
        if not sessions:
            error_panel = Panel(
                "❌ No previous sessions found!",
                style=self.colors["error"],
                box=ROUNDED,
            )
            self.console.print(error_panel)
            return

        # Create the sessions table
        table = Table(
            box=ROUNDED, show_header=True, header_style=self.colors["secondary"]
        )
        table.add_column("#", style=self.colors["secondary"], width=3)
        table.add_column("Session ID", style="bold cyan", width=12)
        table.add_column("Model", style=self.colors["primary"], width=20)
        table.add_column("Preview", style="white", min_width=35)
        table.add_column(
            "Messages", style=self.colors["success"], justify="center", width=8
        )

        # Add session rows
        for i, session in enumerate(sessions, 1):
            # Get preview safely
            try:
                summary = session.get_session_summary()
                preview = (
                    summary.split(": ", 1)[1] if ": " in summary else "Empty session"
                )
                if len(preview) > 35:
                    preview = preview[:32] + "..."
            except Exception:
                preview = "Empty session"

            table.add_row(
                str(i),
                session.session_id,
                session.metadata.model,
                preview,
                str(session.metadata.message_count),
            )

        # Create menu options text
        session_count = len(sessions)
        options_text = Text()
        options_text.append("\n💡 Options:\n", style="bold bright_yellow")
        options_text.append(f"• 📝 Select session (1-{session_count})\n", style="white")
        options_text.append("• 🆕 Type 'new' for new chat\n", style="white")
        options_text.append(
            "• 🗑️ Type '/delete <number>' to delete session\n", style="white"
        )
        options_text.append("• 👋 Type 'q' to quit", style="white")

        # Combine table and options
        from rich.console import Group

        combined_content = Group(table, options_text)

        # Wrap in panel
        sessions_panel = Panel(
            combined_content,
            title="💬 Previous Sessions",
            title_align="left",
            style=self.colors["primary"],
            box=ROUNDED,
        )
        self.console.print(sessions_panel)

    def display_welcome_message(self) -> None:
        """Display the welcome message using Rich styling."""
        # ASCII art in a text object for better control
        mochi_art = """
        .-===-.
        |[:::]|
        `-----´"""

        # Create welcome content
        welcome_text = Text()
        welcome_text.append("🍡 Welcome to ", style="bold bright_magenta")
        welcome_text.append("Mochi-Coco", style="bold bright_white")
        welcome_text.append("!\n\n", style="bold bright_magenta")
        welcome_text.append(mochi_art, style="bright_white bold")
        welcome_text.append("\n\n🤖 ", style="bright_magenta")
        welcome_text.append("AI Chat with Style", style="italic bright_blue")

        welcome_panel = Panel(
            Align.center(welcome_text),
            style=self.colors["primary"],
            box=HEAVY,
            padding=(1, 2),
        )
        self.console.print(welcome_panel)

    def display_chat_history(self, session: ChatSession) -> None:
        """Display the chat history of a session using compact headers like main chat."""
        if not session.messages:
            # Don't show anything if no messages - session info panel will handle this
            return

        # Display messages with compact headers (same style as main chat)
        for i, message in enumerate(session.messages):
            if message.role == "user":
                # Compact user header
                user_header = Panel(
                    "🧑 You",
                    style="bright_cyan",
                    box=ROUNDED,
                    padding=(0, 1),
                    expand=False,
                )
                self.console.print(user_header)

                # Use renderer if available, otherwise print raw content
                if self.renderer:
                    self.renderer.render_static_text(message.content)
                else:
                    self.console.print(message.content)

            elif message.role == "assistant":
                # Modified assistant handling
                self._render_assistant_message(message, i, session)

            elif message.role == "tool":
                # New tool response handling
                self._render_tool_response(message)

            # Add spacing between messages
            self.console.print()

    def _render_assistant_message(self, message, index, session):
        """Render assistant message, checking for tool calls."""

        # Display assistant header
        assistant_header = Panel(
            "🤖 Assistant",
            style="bright_magenta",
            box=ROUNDED,
            padding=(0, 1),
            expand=False,
        )
        self.console.print(assistant_header)

        # Check for tool calls
        if hasattr(message, "tool_calls") and message.tool_calls:
            # Render each tool call
            for tool_call in message.tool_calls:
                self._render_tool_request(tool_call)

            # If message has no content after tool call, skip content rendering
            if not message.content:
                return

        # Render content if present
        if message.content:
            if self.renderer:
                self.renderer.render_static_text(message.content)
            else:
                self.console.print(message.content)

    def _render_tool_request(self, tool_call):
        """Render a tool request panel (without confirmation)."""
        try:
            content = []

            # Tool name section
            tool_text = Text()
            tool_text.append("Tool: ", style="bold")
            tool_name = tool_call.get("function", {}).get("name", "Unknown")
            tool_text.append(tool_name, style="bold cyan")
            content.append(tool_text)

            # Arguments section
            arguments = tool_call.get("function", {}).get("arguments", {})
            if arguments:
                content.append(Text())  # Spacing
                content.append(Text("Arguments:", style="bold"))

                # Format arguments as JSON
                args_json = json.dumps(arguments, indent=2, ensure_ascii=False)
                syntax = Syntax(
                    args_json,
                    "json",
                    theme="monokai",
                    line_numbers=False,
                    background_color="default",
                )
                content.append(syntax)
            else:
                content.append(Text("\nNo arguments", style="dim"))

            # Create panel (similar to ToolConfirmationUI but without interaction)
            content_group = Group(*content)
            panel = Panel(
                content_group,
                title="🤖 AI Tool Request",
                title_align="left",
                style="yellow",  # Same as live tool requests
                box=ROUNDED,
                expand=False,
                padding=(1, 2),
            )

            self.console.print()  # Add spacing before panel
            self.console.print(panel)

        except (KeyError, TypeError, json.JSONDecodeError) as e:
            # Fallback rendering for malformed data
            error_panel = Panel(
                f"[Tool Call - Error rendering details: {str(e)}]",
                style="dim red",
                expand=False,
            )
            self.console.print(error_panel)

    def _render_tool_response(self, message):
        """Render a tool response panel."""
        try:
            # Get tool name from message
            tool_name = getattr(message, "tool_name", "Unknown Tool")

            # Check if the tool execution failed/was denied
            is_error = message.content and (
                message.content.startswith("Error:")
                or "denied" in message.content.lower()
                or "failed" in message.content.lower()
            )

            # Build content based on success/failure
            content = Text()
            if is_error:
                content.append(f"✗ Tool '{tool_name}' failed", style="bold red")
            else:
                content.append(f"✓ Tool '{tool_name}' completed", style="bold green")

            if message.content:
                # Show tool output (truncate if too long)
                display_result = (
                    message.content
                    if len(message.content) <= 500
                    else message.content[:497] + "..."
                )
                content.append("\n\nOutput:\n", style="bold")
                content.append(display_result, style="white")

            # Create panel with appropriate styling
            panel_style = "red" if is_error else "green"
            panel = Panel(content, style=panel_style, box=ROUNDED, expand=False)

            self.console.print()  # Add spacing before panel
            self.console.print(panel)

        except Exception as e:
            # Fallback rendering for errors
            error_panel = Panel(
                f"[Tool Response - Error rendering: {str(e)}]",
                style="dim red",
                expand=False,
            )
            self.console.print(error_panel)

    def display_model_selection_prompt(self, model_count: int) -> None:
        """Display prompt for model selection using Rich styling.

        Note: This method is now integrated into display_models_table()
        and kept for backward compatibility only.
        """
        # Method functionality moved to display_models_table()
        pass

    def display_no_sessions_message(self) -> None:
        """Display message when no previous sessions are found."""
        info_panel = Panel(
            "🆕 No previous sessions found. Let's start a new chat!",
            style=self.colors["info"],
            box=ROUNDED,
        )
        self.console.print(info_panel)

    def display_model_selected(self, model_name: str) -> None:
        """Display confirmation of model selection.

        Note: This method is now a no-op to reduce redundant UI information.
        Model selection is shown in the chat session panel instead.
        """
        # Removed redundant confirmation - model is shown in chat session panel
        pass

    def display_session_loaded(self, session_id: str, model: str) -> None:
        """Display confirmation of session loading.

        Note: This method is now a no-op to reduce redundant UI information.
        Session info is shown in the chat session panel instead.
        """
        # Removed redundant confirmation - session info is shown in chat session panel
        pass

    def display_system_prompts_table(self, prompts: List[SystemPromptInfo]) -> None:
        """Display available system prompts in a Rich table format with integrated options."""
        if not prompts:
            error_panel = Panel(
                "❌ No system prompts found!", style=self.colors["error"], box=ROUNDED
            )
            self.console.print(error_panel)
            return

        # Create the system prompts table
        table = Table(
            box=ROUNDED, show_header=True, header_style=self.colors["secondary"]
        )
        table.add_column("#", style=self.colors["secondary"], width=3)
        table.add_column("Filename", style="bold white", min_width=15)
        table.add_column("Preview", style="white", min_width=35)
        table.add_column(
            "Word Count", style=self.colors["success"], justify="right", width=10
        )

        # Add system prompt rows
        for i, prompt in enumerate(prompts, 1):
            table.add_row(
                str(i), prompt.filename, prompt.preview, str(prompt.word_count)
            )

        # Create system prompt selection options
        prompt_count = len(prompts)
        options_text = Text()
        options_text.append("\n💡 Options:\n", style="bold bright_yellow")
        options_text.append(
            f"• 📝 Select system prompt (1-{prompt_count})\n", style="white"
        )
        options_text.append("• 🆕 Type 'no' for no system prompt\n", style="white")
        options_text.append(
            "• 🗑️ Type '/delete <number>' to delete a system prompt\n", style="white"
        )
        options_text.append("• 👋 Type 'q' to quit", style="white")

        # Combine table and options
        from rich.console import Group

        combined_content = Group(table, options_text)

        # Wrap in panel
        prompts_panel = Panel(
            combined_content,
            title="🔧 System Prompts",
            title_align="left",
            style=self.colors["primary"],
            box=ROUNDED,
        )
        self.console.print(prompts_panel)

    def display_edit_messages_table(self, session: ChatSession) -> None:
        """Display messages for editing with Rich table formatting."""
        if not session.messages:
            error_panel = Panel(
                "❌ No messages to edit in this session.",
                style=self.colors["error"],
                box=ROUNDED,
            )
            self.console.print(error_panel)
            return

        # Create the edit table
        table = Table(
            box=ROUNDED, show_header=True, header_style=self.colors["secondary"]
        )
        table.add_column("#", style=self.colors["secondary"], width=3)
        table.add_column("Role", style="bold", width=12)
        table.add_column("Preview", style="white", min_width=70)

        # Track user message counter
        user_msg_counter = 0

        # Add message rows
        for message in session.messages:
            role = message.role
            preview = (
                message.content[:70] + "..."
                if len(message.content) > 70
                else message.content
            )
            # Clean up preview
            preview = preview.replace("\n", " ").replace("\r", " ")

            if role == "user":
                user_msg_counter += 1
                number = str(user_msg_counter)
                role_display = "🧑 User"
                row_style = "bright_white"
            else:
                number = "-"
                role_display = "🤖 Assistant"
                row_style = "dim"

            table.add_row(number, role_display, preview, style=row_style)

        # Wrap table in panel
        edit_panel = Panel(
            table,
            title="✏️ Edit Messages",
            title_align="left",
            style=self.colors["warning"],
            box=ROUNDED,
        )
        self.console.print(edit_panel)

        # Add prompt
        prompt_text = f"Select a user message (1-{user_msg_counter}) or 'q' to cancel"
        prompt_panel = Panel(prompt_text, style=self.colors["info"], box=ROUNDED)
        self.console.print(prompt_panel)

    def display_command_menu(
        self,
        has_system_prompts: bool = False,
        has_tools: bool = False,
        tool_settings=None,
    ) -> None:
        """Enhanced command menu with dynamic tool options."""

        commands = [
            ("1", "💬 Switch Sessions", "Change to different chat session"),
            ("2", "🤖 Change Model", "Select a different AI model"),
            ("3", "📝 Toggle Markdown", "Enable/disable markdown rendering"),
            ("4", "🤔 Toggle Thinking", "Show/hide thinking blocks"),
        ]

        # Dynamic command numbering
        next_num = 5

        if has_tools:
            # Tool-related commands
            if tool_settings:
                if hasattr(tool_settings, "execution_policy"):
                    policy_status = tool_settings.execution_policy.value.replace(
                        "_", " "
                    ).title()
                else:
                    policy_status = "Never Confirm"
                commands.append(
                    (str(next_num), "🛠️ Tool Policy", f"Current: {policy_status}")
                )
                next_num += 1

                if tool_settings.is_enabled():
                    active_count = (
                        len(tool_settings.tools) if tool_settings.tools else 0
                    )
                    if tool_settings.tool_group:
                        status = f"Group: {tool_settings.tool_group}"
                    else:
                        status = f"{active_count} tool(s) selected"
                    commands.append((str(next_num), "📂 Change Tools", status))
                else:
                    commands.append(
                        (str(next_num), "📂 Select Tools", "No tools selected")
                    )
                next_num += 1
            else:
                commands.append(
                    (str(next_num), "📂 Enable Tools", "Select tools to use")
                )
                next_num += 1

        if has_system_prompts:
            commands.append(
                (str(next_num), "🔧 System Prompt", "Select different system prompt")
            )
            next_num += 1

        # Display the menu
        table = Table(box=ROUNDED, show_header=False, padding=(0, 2))
        table.add_column("Shortcut", style=self.colors["secondary"], width=10)
        table.add_column("Action", style="bold", width=20)
        table.add_column("Description", style="white")

        for cmd, action, desc in commands:
            # Special formatting for shortcuts
            if cmd.isdigit():
                shortcut = f"/{cmd}"
            else:
                shortcut = f"/{cmd}"
            table.add_row(shortcut, action, desc)

        # Add help commands
        # table.add_row("/help", "📚 Help", "Show all available commands", style="dim")
        table.add_row("/quit /q", "👋 Exit", "Exit the menu", style="dim")

        panel = Panel(
            table,
            title="⌨️ Available Commands",
            title_align="left",
            style=self.colors["info"],
            box=ROUNDED,
        )

        self.console.print(panel)

    def display_confirmation_prompt(self, message: str, style: str = "warning") -> None:
        """Display a confirmation prompt with Rich styling."""
        panel_style = self.colors.get(style, style)
        confirmation_panel = Panel(message, style=panel_style, box=ROUNDED)
        self.console.print(confirmation_panel)

    def display_error(self, message: str) -> None:
        """Display an error message with Rich styling."""
        error_panel = Panel(f"❌ {message}", style=self.colors["error"], box=ROUNDED)
        self.console.print(error_panel)

    def display_success(self, message: str) -> None:
        """Display a success message with Rich styling."""
        success_panel = Panel(
            f"✅ {message}", style=self.colors["success"], box=ROUNDED
        )
        self.console.print(success_panel)

    def display_info(self, message: str) -> None:
        """Display an info message with Rich styling."""
        info_panel = Panel(f"💡 {message}", style=self.colors["info"], box=ROUNDED)
        self.console.print(info_panel)
