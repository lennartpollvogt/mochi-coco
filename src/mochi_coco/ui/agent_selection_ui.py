"""
Agent selection UI for interactive agent selection.

This module provides a Rich-based user interface for selecting agents
that can be invoked by the LLM during chat sessions.
"""

from typing import Dict, List, Optional

from rich.box import ROUNDED
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class AgentSelectionUI:
    """UI for selecting agents."""

    def __init__(self):
        self.console = Console()
        self.colors = {
            "primary": "#87CEEB",
            "secondary": "#B0C4DE",
            "warning": "#FFD700",
            "success": "#90EE90",
            "error": "#FFB6C1",
            "info": "#87CEEB",
        }

    def display_agent_selection_menu(
        self,
        agents: Dict[str, str],
        current_selection: Optional[List[str]] = None,
    ) -> None:
        """
        Display the agent selection menu using Rich.

        Args:
            agents: Dict mapping agent names to descriptions
            current_selection: Optional list of selected agent names
        """
        # Show current selection if any
        if current_selection is not None:
            if current_selection:
                self.console.print(
                    f"[green]Currently selected agents: {', '.join(current_selection)}[/green]"
                )
            else:
                self.console.print("[yellow]No agents currently selected[/yellow]")
            self.console.print()

        # Create agents table if there are any
        if agents:
            table = Table(
                box=ROUNDED, show_header=True, header_style=self.colors["secondary"]
            )
            table.add_column("#", style=self.colors["secondary"], width=5)
            table.add_column("Agent Name", style="bold", width=25)
            table.add_column("Description", style="white")

            for i, (agent_name, description) in enumerate(agents.items(), 1):
                table.add_row(str(i), agent_name, description)
        else:
            table = Text(
                "No agents available. Create agents in ./agents/<agent_name>/",
                style="yellow",
            )

        # Create options text
        options_text = Text()
        options_text.append("\n💡 Options:\n", style="bold bright_yellow")
        if agents:
            options_text.append(
                "• 🔢 Select agents by numbers (e.g., 1,3,4 or 1-3)\n", style="white"
            )
        options_text.append("• ❌ Type 'none' to clear selection\n", style="white")
        options_text.append("• 🔄 Type 'reload' to refresh agents\n", style="white")
        options_text.append(
            "• ↩️  Press Enter to keep current selection\n", style="white"
        )
        options_text.append("• 👋 Type 'q' to cancel", style="white")

        # Combine all elements
        content_parts = []
        if isinstance(table, Table):
            content_parts.extend([Text("Agents", style="bold"), table])
        else:
            content_parts.append(table)
        content_parts.append(options_text)

        content = Group(*content_parts)

        panel = Panel(
            content,
            title="🤖 Agent Selection",
            title_align="left",
            style=self.colors["info"],
            box=ROUNDED,
        )

        self.console.print(panel)

    def get_agent_selection(
        self, num_agents: int
    ) -> Optional[tuple[List[int], Optional[str]]]:
        """
        Get user's agent selection.

        Args:
            num_agents: Number of agents available

        Returns:
            Tuple of (selected_indices, special_flag) or None if cancelled
            Special flags:
            - "reload" for reload request
            - "keep" for keeping current selection
            - None for normal selection
        """
        from .user_interaction import UserInteraction

        user_interaction = UserInteraction()
        choice = user_interaction.get_user_input().strip().lower()

        if choice in {"q", "quit", "exit", "cancel"}:
            return None

        if choice == "none":
            return ([], None)

        if choice == "reload":
            return ([], "reload")

        if choice == "" or choice == "keep":
            return ([], "keep")

        # Check for individual selection (numbers with ranges)
        try:
            selected: List[int] = []
            parts = choice.replace(" ", "").split(",")
            for part in parts:
                if "-" in part:
                    # Handle range (e.g., "1-3")
                    start, end = part.split("-", 1)
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    if start_num > end_num:
                        start_num, end_num = end_num, start_num
                    for num in range(start_num, end_num + 1):
                        if 1 <= num <= num_agents:
                            if num - 1 not in selected:
                                selected.append(num - 1)  # Convert to 0-based
                        else:
                            self.console.print(
                                f"[red]Agent number {num} out of range[/red]"
                            )
                            return self.get_agent_selection(num_agents)  # Retry
                else:
                    # Single number
                    agent_num = int(part.strip())
                    if 1 <= agent_num <= num_agents:
                        if agent_num - 1 not in selected:
                            selected.append(agent_num - 1)  # Convert to 0-based
                    else:
                        self.console.print(
                            f"[red]Agent number {agent_num} out of range[/red]"
                        )
                        return self.get_agent_selection(num_agents)  # Retry
            return (selected, None)
        except ValueError:
            self.console.print(f"[red]Invalid selection format: {choice}[/red]")
            return self.get_agent_selection(num_agents)  # Retry
