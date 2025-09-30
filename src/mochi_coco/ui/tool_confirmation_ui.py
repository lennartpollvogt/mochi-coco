"""
Tool confirmation UI for user-friendly confirmation dialogs and result display.

This module provides the ToolConfirmationUI class which handles displaying
tool execution confirmation prompts and results using Rich components.
"""

from typing import Dict, Any, Optional
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.syntax import Syntax
from rich.box import ROUNDED
from rich.console import Group
import json


class ToolConfirmationUI:
    """UI for confirming tool execution."""

    def __init__(self):
        self.console = Console()
        self.colors = {
            "warning": "yellow",
            "success": "green",
            "error": "red",
            "info": "blue",
            "highlight": "cyan",
        }

    def confirm_tool_execution(
        self, tool_name: str, arguments: Dict[str, Any], timeout: Optional[float] = None
    ) -> bool:
        """
        Display confirmation prompt for tool execution.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments that will be passed to the tool
            timeout: Optional timeout in seconds (future enhancement)

        Returns:
            True if user confirms, False otherwise
        """
        # Create the confirmation display
        self._display_tool_request(tool_name, arguments)

        # Get user confirmation (not added to chat history)
        try:
            # Show prompt
            self.console.print(
                "\n⚠️  Allow execution? y/N: ", style="bold yellow", end=""
            )

            response = input().strip().lower()
            confirmed = response in ["y", "yes"]

            # Show confirmation result
            if confirmed:
                self.console.print("[green]✓ Tool execution approved[/green]\n")
            else:
                self.console.print("[red]✗ Tool execution denied[/red]\n")

            return confirmed

        except (EOFError, KeyboardInterrupt):
            self.console.print("\n[red]✗ Tool execution cancelled[/red]\n")
            return False

    def _display_tool_request(self, tool_name: str, arguments: Dict[str, Any]):
        """Display the tool execution request details."""
        # Create content sections
        content = []

        # Tool name section
        tool_text = Text()
        tool_text.append("Tool: ", style="bold")
        tool_text.append(tool_name, style=f"bold {self.colors['highlight']}")
        content.append(tool_text)

        # Arguments section
        if arguments:
            content.append(Text())  # Spacing
            content.append(Text("Arguments:", style="bold"))

            # Format arguments nicely
            args_display = self._format_arguments(arguments)
            if args_display:
                # Use Syntax for JSON highlighting
                syntax = Syntax(
                    args_display,
                    "json",
                    theme="monokai",
                    line_numbers=False,
                    background_color="default",
                )
                content.append(syntax)
        else:
            content.append(Text("\nNo arguments", style="dim"))

        # Create panel
        content_group = Group(*content)

        panel = Panel(
            content_group,
            title="🤖 AI Tool Request",
            title_align="left",
            style=self.colors["warning"],
            box=ROUNDED,
            expand=False,
            padding=(1, 2),
        )

        self.console.print(panel)

    def _format_arguments(self, arguments: Dict[str, Any]) -> str:
        """Format arguments for display in confirmation prompt."""
        if not arguments:
            return "{}"

        try:
            # Pretty print JSON for better readability
            return json.dumps(arguments, indent=2, ensure_ascii=False, default=str)
        except Exception:
            # Fallback to string representation
            return str(arguments)

    def show_tool_result(
        self,
        tool_name: str,
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
        execution_time: Optional[float] = None,
    ):
        """
        Display tool execution result.

        Args:
            tool_name: Name of executed tool
            success: Whether execution was successful
            result: Tool output (if successful)
            error: Error message (if failed)
            execution_time: Execution time in seconds
        """
        if success:
            self._show_success_result(tool_name, result, execution_time)
        else:
            self._show_error_result(tool_name, error, execution_time)

    def _show_success_result(
        self, tool_name: str, result: Optional[str], execution_time: Optional[float]
    ):
        """Display successful execution result."""
        # Build content
        content = Text()
        content.append(f"✓ Tool '{tool_name}' completed", style="bold green")

        if execution_time is not None:
            content.append(f" ({execution_time:.2f}s)", style="dim")

        if result:
            # Truncate long results
            display_result = result if len(result) <= 500 else result[:497] + "..."
            content.append("\n\nOutput:\n", style="bold")
            content.append(display_result, style="white")

        # Show in panel
        panel = Panel(content, style="green", box=ROUNDED, expand=False)
        self.console.print(panel)

    def _show_error_result(
        self, tool_name: str, error: Optional[str], execution_time: Optional[float]
    ):
        """Display error execution result."""
        # Build content
        content = Text()
        content.append(f"✗ Tool '{tool_name}' failed", style="bold red")

        if execution_time is not None:
            content.append(f" ({execution_time:.2f}s)", style="dim")

        if error:
            content.append("\n\nError:\n", style="bold")
            content.append(error, style="white")

        # Show in panel
        panel = Panel(content, style="red", box=ROUNDED, expand=False)
        self.console.print(panel)

    def show_policy_status(self, policy: str):
        """Display current execution policy status."""
        policy_descriptions = {
            "always_confirm": "All tool executions require confirmation",
            "never_confirm": "Tools execute automatically without confirmation",
            "confirm_destructive": "Only destructive operations require confirmation",
        }

        description = policy_descriptions.get(policy, policy)

        panel = Panel(
            f"[bold]Current Policy:[/bold] {description}",
            title="🛠️ Tool Execution Policy",
            style=self.colors["info"],
            box=ROUNDED,
        )

        self.console.print(panel)
