"""
Tool execution service for safely executing user tools with confirmation policies.

This module provides the ToolExecutionService class which handles the safe execution
of user-defined tools with proper error handling, confirmation policies, and execution tracking.
"""

from typing import Dict, Callable, Any, Optional, List
from dataclasses import dataclass
import time
import logging
from .config import ToolExecutionPolicy

logger = logging.getLogger(__name__)

@dataclass
class ToolExecutionResult:
    """Result of tool execution."""
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time: float = 0.0
    tool_name: Optional[str] = None

class ToolExecutionService:
    """Service for safely executing user tools."""

    def __init__(self, available_functions: Dict[str, Callable]):
        self.available_functions = available_functions
        self.execution_history: List[ToolExecutionResult] = []
        self.max_history_size = 100

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any],
                    policy: ToolExecutionPolicy = ToolExecutionPolicy.ALWAYS_CONFIRM,
                    confirm_callback: Optional[Callable] = None) -> ToolExecutionResult:
        """
        Execute a tool with given arguments.

        Args:
            tool_name: Name of the tool function
            arguments: Dictionary of arguments to pass to the function
            policy: Execution policy for confirmation
            confirm_callback: Optional callback for confirmation UI

        Returns:
            ToolExecutionResult with success status and result/error
        """
        start_time = time.time()

        # Validate tool exists
        if not self._validate_tool_exists(tool_name):
            result = ToolExecutionResult(
                success=False,
                result=None,
                error_message=f"Tool '{tool_name}' not found",
                execution_time=time.time() - start_time,
                tool_name=tool_name
            )
            self._add_to_history(result)
            return result

        # Check confirmation policy
        if policy == ToolExecutionPolicy.ALWAYS_CONFIRM and confirm_callback:
            if not confirm_callback(tool_name, arguments):
                result = ToolExecutionResult(
                    success=False,
                    result=None,
                    error_message="Tool execution denied by user",
                    execution_time=time.time() - start_time,
                    tool_name=tool_name
                )
                self._add_to_history(result)
                return result
        elif policy == ToolExecutionPolicy.CONFIRM_DESTRUCTIVE:
            # Future enhancement: Check if tool is marked as destructive
            # For now, treat as ALWAYS_CONFIRM
            if confirm_callback and not confirm_callback(tool_name, arguments):
                result = ToolExecutionResult(
                    success=False,
                    result=None,
                    error_message="Tool execution denied by user",
                    execution_time=time.time() - start_time,
                    tool_name=tool_name
                )
                self._add_to_history(result)
                return result

        # Execute the tool
        try:
            func = self.available_functions[tool_name]
            logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")

            # Execute with timeout protection (future enhancement)
            result_value = func(**arguments)

            # Ensure result is string for LLM
            if result_value is None:
                result_str = "Tool executed successfully (no output)"
            else:
                result_str = str(result_value)

            result = ToolExecutionResult(
                success=True,
                result=result_str,
                execution_time=time.time() - start_time,
                tool_name=tool_name
            )
            self._add_to_history(result)
            logger.info(f"Tool '{tool_name}' executed successfully in {result.execution_time:.2f}s")
            return result

        except TypeError as e:
            # Invalid arguments
            error_msg = f"Invalid arguments for tool '{tool_name}': {e}"
            logger.error(error_msg)
            result = ToolExecutionResult(
                success=False,
                result=None,
                error_message=error_msg,
                execution_time=time.time() - start_time,
                tool_name=tool_name
            )
            self._add_to_history(result)
            return result

        except Exception as e:
            # General execution error
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            result = ToolExecutionResult(
                success=False,
                result=None,
                error_message=error_msg,
                execution_time=time.time() - start_time,
                tool_name=tool_name
            )
            self._add_to_history(result)
            return result

    def _validate_tool_exists(self, tool_name: str) -> bool:
        """Validate that the requested tool exists."""
        return tool_name in self.available_functions

    def _add_to_history(self, result: ToolExecutionResult):
        """Add execution result to history with size limit."""
        self.execution_history.append(result)
        # Trim history if it exceeds max size
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]

    def clear_history(self):
        """Clear execution history."""
        self.execution_history.clear()

    def get_recent_executions(self, limit: int = 10) -> List[ToolExecutionResult]:
        """Get recent tool executions."""
        return self.execution_history[-limit:] if self.execution_history else []

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get statistics about tool executions."""
        if not self.execution_history:
            return {
                'total_executions': 0,
                'successful': 0,
                'failed': 0,
                'average_time': 0.0
            }

        successful = sum(1 for r in self.execution_history if r.success)
        failed = len(self.execution_history) - successful
        avg_time = sum(r.execution_time for r in self.execution_history) / len(self.execution_history)

        return {
            'total_executions': len(self.execution_history),
            'successful': successful,
            'failed': failed,
            'average_time': avg_time
        }
