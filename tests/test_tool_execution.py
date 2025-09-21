"""
Unit tests for tool execution service.

This module contains comprehensive tests for the ToolExecutionService class,
testing all execution scenarios, error handling, and policy enforcement.
"""

from unittest.mock import Mock
import time

from mochi_coco.tools.execution_service import ToolExecutionService, ToolExecutionResult
from mochi_coco.tools.config import ToolExecutionPolicy

class TestToolExecution:

    def test_execute_successful_tool(self):
        """Test successful tool execution."""
        def test_tool(x: int) -> str:
            return f"Result: {x}"

        service = ToolExecutionService({'test_tool': test_tool})
        result = service.execute_tool('test_tool', {'x': 42},
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert result.success
        assert result.result == "Result: 42"
        assert result.tool_name == 'test_tool'
        assert result.execution_time > 0
        assert result.error_message is None

    def test_execute_nonexistent_tool(self):
        """Test execution of non-existent tool."""
        service = ToolExecutionService({})
        result = service.execute_tool('missing_tool', {},
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert not result.success
        assert "not found" in result.error_message.lower()
        assert result.result is None
        assert result.tool_name == 'missing_tool'

    def test_execute_with_invalid_arguments(self):
        """Test execution with invalid arguments."""
        def test_tool(x: int) -> str:
            return f"Result: {x}"

        service = ToolExecutionService({'test_tool': test_tool})
        result = service.execute_tool('test_tool', {'y': 42},  # wrong arg name
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert not result.success
        assert "invalid arguments" in result.error_message.lower()

    def test_execute_with_missing_arguments(self):
        """Test execution with missing required arguments."""
        def test_tool(x: int, y: int) -> str:
            return f"Result: {x + y}"

        service = ToolExecutionService({'test_tool': test_tool})
        result = service.execute_tool('test_tool', {'x': 42},  # missing y
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert not result.success
        assert "missing" in result.error_message.lower() or "required" in result.error_message.lower()

    def test_execute_tool_with_exception(self):
        """Test execution when tool raises exception."""
        def failing_tool():
            raise ValueError("Tool error")

        service = ToolExecutionService({'failing_tool': failing_tool})
        result = service.execute_tool('failing_tool', {},
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert not result.success
        assert "Tool error" in result.error_message

    def test_execute_with_confirmation_approved(self):
        """Test execution with confirmation callback that approves."""
        def test_tool() -> str:
            return "Success"

        service = ToolExecutionService({'test_tool': test_tool})

        # Mock confirmation callback that approves
        confirm_callback = Mock(return_value=True)
        result = service.execute_tool('test_tool', {},
                                     ToolExecutionPolicy.ALWAYS_CONFIRM,
                                     confirm_callback)

        assert result.success
        assert result.result == "Success"
        confirm_callback.assert_called_once_with('test_tool', {})

    def test_execute_with_confirmation_denied(self):
        """Test execution with confirmation callback that denies."""
        def test_tool() -> str:
            return "Success"

        service = ToolExecutionService({'test_tool': test_tool})

        # Mock confirmation callback that denies
        confirm_callback = Mock(return_value=False)
        result = service.execute_tool('test_tool', {},
                                     ToolExecutionPolicy.ALWAYS_CONFIRM,
                                     confirm_callback)

        assert not result.success
        assert "denied by user" in result.error_message.lower()
        confirm_callback.assert_called_once_with('test_tool', {})

    def test_execute_never_confirm_policy(self):
        """Test that NEVER_CONFIRM policy skips confirmation."""
        def test_tool() -> str:
            return "Success"

        service = ToolExecutionService({'test_tool': test_tool})

        # Confirmation callback should not be called
        confirm_callback = Mock(return_value=False)
        result = service.execute_tool('test_tool', {},
                                     ToolExecutionPolicy.NEVER_CONFIRM,
                                     confirm_callback)

        assert result.success
        confirm_callback.assert_not_called()

    def test_execute_confirm_destructive_policy(self):
        """Test CONFIRM_DESTRUCTIVE policy (currently treated as ALWAYS_CONFIRM)."""
        def test_tool() -> str:
            return "Success"

        service = ToolExecutionService({'test_tool': test_tool})

        # Mock confirmation callback that denies
        confirm_callback = Mock(return_value=False)
        result = service.execute_tool('test_tool', {},
                                     ToolExecutionPolicy.CONFIRM_DESTRUCTIVE,
                                     confirm_callback)

        assert not result.success
        assert "denied by user" in result.error_message.lower()
        confirm_callback.assert_called_once_with('test_tool', {})

    def test_execute_always_confirm_without_callback(self):
        """Test ALWAYS_CONFIRM policy without confirmation callback provided."""
        def test_tool() -> str:
            return "Success"

        service = ToolExecutionService({'test_tool': test_tool})
        result = service.execute_tool('test_tool', {},
                                     ToolExecutionPolicy.ALWAYS_CONFIRM,
                                     None)  # No callback

        # Should still execute since no callback provided
        assert result.success
        assert result.result == "Success"

    def test_execution_history(self):
        """Test that execution history is maintained."""
        def test_tool(x: int) -> str:
            return str(x)

        service = ToolExecutionService({'test_tool': test_tool})

        # Execute multiple times
        service.execute_tool('test_tool', {'x': 1}, ToolExecutionPolicy.NEVER_CONFIRM)
        service.execute_tool('test_tool', {'x': 2}, ToolExecutionPolicy.NEVER_CONFIRM)
        service.execute_tool('missing_tool', {}, ToolExecutionPolicy.NEVER_CONFIRM)

        history = service.get_recent_executions(10)
        assert len(history) == 3
        assert history[0].result == "1"
        assert history[1].result == "2"
        assert not history[2].success

    def test_execution_stats(self):
        """Test execution statistics."""
        def test_tool() -> str:
            time.sleep(0.01)  # Small delay for timing
            return "Success"

        service = ToolExecutionService({'test_tool': test_tool})

        # Execute successfully twice
        service.execute_tool('test_tool', {}, ToolExecutionPolicy.NEVER_CONFIRM)
        service.execute_tool('test_tool', {}, ToolExecutionPolicy.NEVER_CONFIRM)

        # Execute with failure once
        service.execute_tool('missing_tool', {}, ToolExecutionPolicy.NEVER_CONFIRM)

        stats = service.get_execution_stats()
        assert stats['total_executions'] == 3
        assert stats['successful'] == 2
        assert stats['failed'] == 1
        assert stats['average_time'] > 0

    def test_execution_stats_empty_history(self):
        """Test execution statistics with empty history."""
        service = ToolExecutionService({})

        stats = service.get_execution_stats()
        assert stats['total_executions'] == 0
        assert stats['successful'] == 0
        assert stats['failed'] == 0
        assert stats['average_time'] == 0.0

    def test_none_return_value_handling(self):
        """Test handling of None return values."""
        def test_tool() -> None:
            return None

        service = ToolExecutionService({'test_tool': test_tool})
        result = service.execute_tool('test_tool', {},
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert result.success
        assert "no output" in result.result.lower()

    def test_clear_history(self):
        """Test clearing execution history."""
        def test_tool() -> str:
            return "Success"

        service = ToolExecutionService({'test_tool': test_tool})

        # Add some history
        service.execute_tool('test_tool', {}, ToolExecutionPolicy.NEVER_CONFIRM)
        service.execute_tool('test_tool', {}, ToolExecutionPolicy.NEVER_CONFIRM)

        assert len(service.execution_history) == 2

        # Clear history
        service.clear_history()
        assert len(service.execution_history) == 0

        # Stats should reflect empty history
        stats = service.get_execution_stats()
        assert stats['total_executions'] == 0

    def test_history_size_limit(self):
        """Test that execution history respects size limit."""
        def test_tool(x: int) -> str:
            return str(x)

        service = ToolExecutionService({'test_tool': test_tool})
        service.max_history_size = 5  # Set small limit for testing

        # Execute more than the limit
        for i in range(10):
            service.execute_tool('test_tool', {'x': i}, ToolExecutionPolicy.NEVER_CONFIRM)

        # History should be trimmed to max size
        assert len(service.execution_history) == 5
        # Should keep the most recent executions
        assert service.execution_history[0].result == "5"
        assert service.execution_history[-1].result == "9"

    def test_get_recent_executions_limit(self):
        """Test get_recent_executions with limit parameter."""
        def test_tool(x: int) -> str:
            return str(x)

        service = ToolExecutionService({'test_tool': test_tool})

        # Execute several times
        for i in range(5):
            service.execute_tool('test_tool', {'x': i}, ToolExecutionPolicy.NEVER_CONFIRM)

        # Get recent with limit
        recent = service.get_recent_executions(3)
        assert len(recent) == 3
        assert recent[0].result == "2"  # Third-to-last
        assert recent[-1].result == "4"  # Last

    def test_get_recent_executions_empty_history(self):
        """Test get_recent_executions with empty history."""
        service = ToolExecutionService({})

        recent = service.get_recent_executions(10)
        assert recent == []

    def test_tool_execution_result_dataclass(self):
        """Test ToolExecutionResult dataclass functionality."""
        result = ToolExecutionResult(
            success=True,
            result="Test result",
            error_message=None,
            execution_time=1.5,
            tool_name="test_tool"
        )

        assert result.success
        assert result.result == "Test result"
        assert result.error_message is None
        assert result.execution_time == 1.5
        assert result.tool_name == "test_tool"

    def test_complex_argument_types(self):
        """Test execution with complex argument types."""
        def complex_tool(data: dict, items: list, count: int = 5) -> str:
            return f"Data: {data}, Items: {items}, Count: {count}"

        service = ToolExecutionService({'complex_tool': complex_tool})

        complex_args = {
            'data': {'key': 'value', 'nested': {'inner': 42}},
            'items': [1, 2, 3, 'string'],
            'count': 10
        }

        result = service.execute_tool('complex_tool', complex_args,
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert result.success
        assert "Data:" in result.result
        assert "Items:" in result.result
        assert "Count: 10" in result.result

    def test_tool_with_default_arguments(self):
        """Test execution of tools with default arguments."""
        def tool_with_defaults(required: str, optional: str = "default") -> str:
            return f"{required}-{optional}"

        service = ToolExecutionService({'tool_with_defaults': tool_with_defaults})

        # Test with only required argument
        result = service.execute_tool('tool_with_defaults', {'required': 'test'},
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert result.success
        assert result.result == "test-default"

        # Test with both arguments
        result = service.execute_tool('tool_with_defaults',
                                     {'required': 'test', 'optional': 'custom'},
                                     ToolExecutionPolicy.NEVER_CONFIRM)

        assert result.success
        assert result.result == "test-custom"

class TestToolExecutionIntegration:
    """Integration tests for tool execution with other components."""

    def test_tool_execution_with_discovery_service(self):
        """Test integration with tool discovery service."""
        from mochi_coco.tools.discovery_service import ToolDiscoveryService
        import tempfile
        import os

        # Create temporary tools directory
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_dir = os.path.join(temp_dir, "tools")
            os.makedirs(tools_dir)

            # Create test tools
            init_content = '''
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

__all__ = ['add_numbers', 'greet']
'''
            with open(os.path.join(tools_dir, "__init__.py"), 'w') as f:
                f.write(init_content)

            # Discover tools
            discovery = ToolDiscoveryService(tools_dir)
            functions, groups = discovery.discover_tools()

            # Create execution service with discovered tools
            execution = ToolExecutionService(functions)

            # Test execution
            result = execution.execute_tool('add_numbers', {'a': 5, 'b': 3},
                                          ToolExecutionPolicy.NEVER_CONFIRM)

            assert result.success
            assert result.result == "8"

            result = execution.execute_tool('greet', {'name': 'World'},
                                          ToolExecutionPolicy.NEVER_CONFIRM)

            assert result.success
            assert result.result == "Hello, World!"
