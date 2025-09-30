"""
Tool selection UI for interactive tool and tool group selection.

This module provides a Rich-based user interface for selecting individual tools
or tool groups that can be used by LLMs during chat sessions.
"""

from typing import Dict, List, Optional, Tuple
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group
from rich.text import Text
from rich.box import ROUNDED

class ToolSelectionUI:
    """UI for selecting tools and tool groups."""

    def __init__(self):
        self.console = Console()
        self.colors = {
            'primary': '#87CEEB',
            'secondary': '#B0C4DE',
            'warning': '#FFD700',
            'success': '#90EE90',
            'error': '#FFB6C1',
            'info': '#87CEEB'
        }

    def display_tool_selection_menu(self,
                                   individual_tools: Dict[str, str],
                                   tool_groups: Dict[str, List[str]],
                                   current_selection: Optional[Tuple[List[str], Optional[str]]] = None) -> None:
        """
        Display the tool selection menu using Rich.

        Args:
            individual_tools: Dict mapping tool names to descriptions
            tool_groups: Dict mapping group names to list of tool names
            current_selection: Optional tuple of (selected_tools, selected_group)
        """

        # Show current selection if any
        if current_selection:
            selected_tools, selected_group = current_selection
            if selected_group:
                self.console.print(f"[green]Currently selected group: {selected_group}[/green]")
            elif selected_tools:
                self.console.print(f"[green]Currently selected tools: {', '.join(selected_tools)}[/green]")
            else:
                self.console.print("[yellow]No tools currently selected[/yellow]")
            self.console.print()

        # Create single tools table if there are any
        if individual_tools:
            single_table = Table(box=ROUNDED, show_header=True, header_style=self.colors['secondary'])
            single_table.add_column("#", style=self.colors['secondary'], width=5)
            single_table.add_column("Tool Name", style="bold", width=25)
            single_table.add_column("Description", style="white")

            for i, (tool_name, description) in enumerate(individual_tools.items(), 1):
                single_table.add_row(str(i), tool_name, description)
        else:
            single_table = Text("No individual tools available", style="dim")

        # Create tool groups table if there are any
        if tool_groups:
            group_table = Table(box=ROUNDED, show_header=True, header_style=self.colors['secondary'])
            group_table.add_column("Letter", style=self.colors['secondary'], width=8)
            group_table.add_column("Group Name", style="bold", width=25)
            group_table.add_column("Tools Included", style="white")

            for i, (group_name, tools) in enumerate(tool_groups.items()):
                letter = chr(ord('a') + i)
                tools_str = ", ".join(tools)
                if len(tools_str) > 50:
                    tools_str = tools_str[:47] + "..."
                group_table.add_row(letter, group_name, tools_str)
        else:
            group_table = Text("No tool groups available", style="dim")

        # Create options text
        options_text = Text()
        options_text.append("\n💡 Options:\n", style="bold bright_yellow")
        if individual_tools:
            options_text.append("• 🔢 Select tools by numbers (e.g., 1,3,4 or 1-3)\n", style="white")
        if tool_groups:
            options_text.append("• 📂 Select a group by letter (e.g., a)\n", style="white")
        options_text.append("• ❌ Type 'none' to clear selection\n", style="white")
        options_text.append("• 🔄 Type 'reload' to refresh tools\n", style="white")
        options_text.append("• ↩️  Press Enter to keep current selection\n", style="white")
        options_text.append("• 👋 Type 'q' to cancel", style="white")

        # Combine all elements
        content_parts = []
        if isinstance(single_table, Table):
            content_parts.extend([Text("Individual Tools", style="bold"), single_table])
        if isinstance(group_table, Table):
            if content_parts:
                content_parts.append(Text())  # Add spacing
            content_parts.extend([Text("Tool Groups", style="bold"), group_table])
        if not content_parts:
            content_parts.append(Text("No tools available. Place Python functions in ./tools/__init__.py",
                                     style="yellow"))
        content_parts.append(options_text)

        content = Group(*content_parts)

        panel = Panel(
            content,
            title="🛠️ Tool Selection",
            title_align="left",
            style=self.colors['info'],
            box=ROUNDED
        )

        self.console.print(panel)

    def get_tool_selection(self, num_tools: int, num_groups: int) -> Optional[Tuple[List[int], bool, Optional[str]]]:
        """
        Get user's tool selection.

        Args:
            num_tools: Number of individual tools available
            num_groups: Number of tool groups available

        Returns:
            Tuple of (selected_indices, is_group_selection, special_flag) or None if cancelled
            Special flags:
            - "reload" for reload request
            - "keep" for keeping current selection
            - None for normal selection
        """
        from .user_interaction import UserInteraction

        user_interaction = UserInteraction()
        choice = user_interaction.get_user_input().strip().lower()

        if choice in {'q', 'quit', 'exit', 'cancel'}:
            return None

        if choice == 'none':
            return ([], False, None)

        if choice == 'reload':
            return ([], False, "reload")

        if choice == '' or choice == 'keep':
            return ([], False, "keep")

        # Check for group selection (single letter)
        if len(choice) == 1 and choice.isalpha():
            group_index = ord(choice) - ord('a')
            if 0 <= group_index < num_groups:
                return ([group_index], True, None)
            else:
                self.console.print(f"[red]Invalid group selection: {choice}[/red]")
                return self.get_tool_selection(num_tools, num_groups)  # Retry

        # Check for individual tool selection (numbers with ranges)
        try:
            selected = []
            parts = choice.replace(' ', '').split(',')
            for part in parts:
                if '-' in part:
                    # Handle range (e.g., "1-3")
                    start, end = part.split('-', 1)
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    if start_num > end_num:
                        start_num, end_num = end_num, start_num
                    for num in range(start_num, end_num + 1):
                        if 1 <= num <= num_tools:
                            if num - 1 not in selected:
                                selected.append(num - 1)  # Convert to 0-based
                        else:
                            self.console.print(f"[red]Tool number {num} out of range[/red]")
                            return self.get_tool_selection(num_tools, num_groups)  # Retry
                else:
                    # Single number
                    tool_num = int(part.strip())
                    if 1 <= tool_num <= num_tools:
                        if tool_num - 1 not in selected:
                            selected.append(tool_num - 1)  # Convert to 0-based
                    else:
                        self.console.print(f"[red]Tool number {tool_num} out of range[/red]")
                        return self.get_tool_selection(num_tools, num_groups)  # Retry
            return (selected, False, None)
        except ValueError:
            self.console.print(f"[red]Invalid selection format: {choice}[/red]")
            return self.get_tool_selection(num_tools, num_groups)  # Retry
