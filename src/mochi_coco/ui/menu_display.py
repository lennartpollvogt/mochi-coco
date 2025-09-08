"""
Menu display utilities using Rich for consistent and beautiful formatting.
"""

from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED, HEAVY
from rich.align import Align

from ..ollama import OllamaClient, ModelInfo
from ..chat import ChatSession
from ..rendering import MarkdownRenderer


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
            'primary': 'bright_magenta',
            'secondary': 'bright_cyan',
            'success': 'bright_green',
            'warning': 'bright_yellow',
            'error': 'bright_red',
            'info': 'bright_blue',
            'muted': 'bright_black'
        }

    def display_models_table(self, models: List[ModelInfo], client: OllamaClient) -> None:
        """Display available models in a Rich table format."""
        if not models:
            error_panel = Panel(
                "❌ No models found!",
                style=self.colors['error'],
                box=ROUNDED
            )
            self.console.print(error_panel)
            return

        # Create the models table
        table = Table(box=ROUNDED, show_header=True, header_style=self.colors['secondary'])
        table.add_column("#", style=self.colors['secondary'], width=3)
        table.add_column("Model Name", style="bold white", min_width=25)
        table.add_column("Size (MB)", style=self.colors['info'], justify="right", width=12)
        table.add_column("Family", style=self.colors['warning'], width=15)
        table.add_column("Max. Context", style=self.colors['success'], justify="right", width=12)

        # Add model rows
        for i, model in enumerate(models, 1):
            size_str = f"{model.size_mb:.1f}" if model.size_mb else "N/A"
            family_str = model.family or "N/A"

            # Get context length safely
            max_context_window = "N/A"
            try:
                if model.name:
                    model_details = client.show_model_details(model.name)
                    if model_details:
                        model_info = model_details.model_dump()
                        if 'modelinfo' in model_info and f'{family_str}.context_length' in model_info['modelinfo']:
                            max_context_window = str(model_info['modelinfo'][f'{family_str}.context_length'])
            except Exception:
                pass

            table.add_row(
                str(i),
                model.name or "Unknown",
                size_str,
                family_str,
                max_context_window
            )

        # Wrap table in panel
        models_panel = Panel(
            table,
            title="🤖 Available Models",
            title_align="left",
            style=self.colors['primary'],
            box=ROUNDED
        )
        self.console.print(models_panel)

        # Add attention notice
        attention_text = Text()
        attention_text.append("⚠️  ATTENTION: ", style="bold bright_red")
        attention_text.append("The maximum context length is the supported length of the model ", style="yellow")
        attention_text.append("but not the actual length during chat sessions.\n", style="yellow")
        attention_text.append("💡 ", style="bright_blue")
        attention_text.append("Open Ollama application to set default context length!", style="bright_blue")

        attention_panel = Panel(
            attention_text,
            style=self.colors['warning'],
            box=ROUNDED
        )
        self.console.print(attention_panel)

    def display_sessions_table(self, sessions: List[ChatSession]) -> None:
        """Display available sessions in a Rich table format."""
        if not sessions:
            error_panel = Panel(
                "❌ No previous sessions found!",
                style=self.colors['error'],
                box=ROUNDED
            )
            self.console.print(error_panel)
            return

        # Create the sessions table
        table = Table(box=ROUNDED, show_header=True, header_style=self.colors['secondary'])
        table.add_column("#", style=self.colors['secondary'], width=2)
        table.add_column("Session ID", style="bold cyan", width=12)
        table.add_column("Model", style=self.colors['primary'], width=17)
        table.add_column("Preview", style="white", min_width=28)
        table.add_column("Messages", style=self.colors['success'], justify="center", width=8)

        # Add session rows
        for i, session in enumerate(sessions, 1):
            # Get preview safely
            try:
                summary = session.get_session_summary()
                preview = summary.split(': ', 1)[1] if ': ' in summary else "Empty session"
                if len(preview) > 35:
                    preview = preview[:32] + "..."
            except Exception:
                preview = "Empty session"

            table.add_row(
                str(i),
                session.session_id,
                session.metadata.model,
                preview,
                str(session.metadata.message_count)
            )

        # Wrap table in panel
        sessions_panel = Panel(
            table,
            title="💬 Previous Sessions",
            title_align="left",
            style=self.colors['primary'],
            box=ROUNDED
        )
        self.console.print(sessions_panel)

    def display_menu_help(self, session_count: int) -> None:
        """Display help text for menu options using Rich panels."""
        options = [
            f"📝 Select session (1-{session_count})",
            "🆕 Type 'new' for new chat",
            "🗑️  Type '/delete <number>' to delete session",
            "👋 Type 'q' to quit"
        ]

        help_text = "\n".join(f"• {option}" for option in options)

        help_panel = Panel(
            help_text,
            title="💡 Options",
            title_align="left",
            style=self.colors['info'],
            box=ROUNDED
        )
        self.console.print(help_panel)

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
        welcome_text.append("AI Chat with Flavor", style="italic bright_blue")

        welcome_panel = Panel(
            Align.center(welcome_text),
            style=self.colors['primary'],
            box=HEAVY,
            padding=(1, 2)
        )
        self.console.print(welcome_panel)

    def display_chat_history(self, session: ChatSession) -> None:
        """Display the chat history of a session using Rich formatting."""
        if not session.messages:
            info_panel = Panel(
                "📝 No previous messages in this session.",
                style=self.colors['info'],
                box=ROUNDED
            )
            self.console.print(info_panel)
            return

        # Session info header
        session_info = Text()
        session_info.append("Session ID: ", style="bold")
        session_info.append(session.session_id, style="cyan")
        session_info.append(" | Model: ", style="bold")
        session_info.append(session.model, style="magenta")

        header_panel = Panel(
            session_info,
            title="📜 Chat History",
            title_align="left",
            style=self.colors['info'],
            box=ROUNDED
        )
        self.console.print(header_panel)

        # Display messages
        for i, message in enumerate(session.messages):
            if message.role == "user":
                user_panel = Panel(
                    message.content,
                    title="🧑 You",
                    title_align="left",
                    style="bright_cyan",
                    box=ROUNDED,
                    padding=(0, 1)
                )
                self.console.print(user_panel)
            elif message.role == "assistant":
                assistant_panel = Panel(
                    message.content,
                    title="🤖 Assistant",
                    title_align="left",
                    style="bright_magenta",
                    box=ROUNDED,
                    padding=(0, 1)
                )
                self.console.print(assistant_panel)

            # Add spacing between messages
            if i < len(session.messages) - 1:
                self.console.print()

    def display_model_selection_header(self) -> None:
        """Display header for model selection."""
        header_panel = Panel(
            "🤖 Select your AI model",
            style=self.colors['primary'],
            box=ROUNDED
        )
        self.console.print(header_panel)

    def display_model_selection_prompt(self, model_count: int) -> None:
        """Display prompt for model selection using Rich styling."""
        prompt_text = f"Select a model (1-{model_count}) or 'q' to quit"
        prompt_panel = Panel(
            prompt_text,
            style=self.colors['warning'],
            box=ROUNDED
        )
        self.console.print(prompt_panel)

    def display_no_sessions_message(self) -> None:
        """Display message when no previous sessions are found."""
        info_panel = Panel(
            "🆕 No previous sessions found. Let's start a new chat!",
            style=self.colors['info'],
            box=ROUNDED
        )
        self.console.print(info_panel)

    def display_model_selected(self, model_name: str) -> None:
        """Display confirmation of model selection."""
        success_text = Text()
        success_text.append("✅ Selected model: ", style="bold green")
        success_text.append(model_name, style="bold magenta")

        success_panel = Panel(
            success_text,
            style=self.colors['success'],
            box=ROUNDED
        )
        self.console.print(success_panel)

    def display_session_loaded(self, session_id: str, model: str) -> None:
        """Display confirmation of session loading."""
        success_text = Text()
        success_text.append("✅ Loaded session: ", style="bold green")
        success_text.append(session_id, style="bold cyan")
        success_text.append(" with ", style="bold green")
        success_text.append(model, style="bold magenta")

        success_panel = Panel(
            success_text,
            style=self.colors['success'],
            box=ROUNDED
        )
        self.console.print(success_panel)

    def display_edit_messages_table(self, session: ChatSession) -> None:
        """Display messages for editing with Rich table formatting."""
        if not session.messages:
            error_panel = Panel(
                "❌ No messages to edit in this session.",
                style=self.colors['error'],
                box=ROUNDED
            )
            self.console.print(error_panel)
            return

        # Create the edit table
        table = Table(box=ROUNDED, show_header=True, header_style=self.colors['secondary'])
        table.add_column("#", style=self.colors['secondary'], width=3)
        table.add_column("Role", style="bold", width=12)
        table.add_column("Preview", style="white", min_width=70)

        # Track user message counter
        user_msg_counter = 0

        # Add message rows
        for message in session.messages:
            role = message.role
            preview = message.content[:70] + "..." if len(message.content) > 70 else message.content
            # Clean up preview
            preview = preview.replace('\n', ' ').replace('\r', ' ')

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
            title="✏️  Edit Messages",
            title_align="left",
            style=self.colors['warning'],
            box=ROUNDED
        )
        self.console.print(edit_panel)

        # Add prompt
        prompt_text = f"Select a user message (1-{user_msg_counter}) or 'q' to cancel"
        prompt_panel = Panel(
            prompt_text,
            style=self.colors['info'],
            box=ROUNDED
        )
        self.console.print(prompt_panel)

    def display_command_menu(self) -> None:
        """Display the command menu using Rich panels."""
        # Create command options as individual panels
        commands = [
            ("1", "💬 Switch Sessions", "Change to different chat session"),
            ("2", "🤖 Change Model", "Select a different AI model"),
            ("3", "📝 Toggle Markdown", "Enable/disable markdown rendering"),
            ("4", "🤔 Toggle Thinking", "Show/hide thinking blocks")
        ]

        # Create table for commands
        table = Table(box=ROUNDED, show_header=True, header_style=self.colors['secondary'])
        table.add_column("#", style=self.colors['secondary'], width=3)
        table.add_column("Command", style="bold", width=20)
        table.add_column("Description", style="white", min_width=30)

        for number, command, description in commands:
            table.add_row(number, command, description)

        # Wrap in panel
        menu_panel = Panel(
            table,
            title="⚙️  Command Menu",
            title_align="left",
            style=self.colors['info'],
            box=ROUNDED
        )
        self.console.print(menu_panel)

        # Add prompt
        prompt_panel = Panel(
            "Select an option (1-4) or 'q' to cancel",
            style=self.colors['warning'],
            box=ROUNDED
        )
        self.console.print(prompt_panel)

    def display_confirmation_prompt(self, message: str, style: str = "warning") -> None:
        """Display a confirmation prompt with Rich styling."""
        panel_style = self.colors.get(style, style)
        confirmation_panel = Panel(
            message,
            style=panel_style,
            box=ROUNDED
        )
        self.console.print(confirmation_panel)

    def display_error(self, message: str) -> None:
        """Display an error message with Rich styling."""
        error_panel = Panel(
            f"❌ {message}",
            style=self.colors['error'],
            box=ROUNDED
        )
        self.console.print(error_panel)

    def display_success(self, message: str) -> None:
        """Display a success message with Rich styling."""
        success_panel = Panel(
            f"✅ {message}",
            style=self.colors['success'],
            box=ROUNDED
        )
        self.console.print(success_panel)

    def display_info(self, message: str) -> None:
        """Display an info message with Rich styling."""
        info_panel = Panel(
            f"💡 {message}",
            style=self.colors['info'],
            box=ROUNDED
        )
        self.console.print(info_panel)
