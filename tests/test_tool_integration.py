import pytest
from unittest.mock import Mock
from pathlib import Path

from mochi_coco.tools.discovery_service import ToolDiscoveryService
from mochi_coco.tools.execution_service import ToolExecutionService
from mochi_coco.tools.schema_service import ToolSchemaService
from mochi_coco.tools.config import ToolSettings, ToolExecutionPolicy
from mochi_coco.chat.session import ChatSession


class TestToolIntegration:
    """Integration tests for tool functionality."""

    @pytest.fixture
    def temp_tools_dir(self, tmp_path):
        """Create a temporary tools directory with test tools."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create a comprehensive test tools file
        tools_content = '''
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.

    Args:
        expression: Mathematical expression (e.g., "2 + 2")

    Returns:
        str: Result of the calculation
    """
    try:
        # Safe evaluation - only basic math
        allowed_chars = set('0123456789+-*/()., ')
        if not all(c in allowed_chars for c in expression):
            return f"Error: Invalid characters in expression"

        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

def get_time() -> str:
    """
    Get the current time.

    Returns:
        str: Current time as a string
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def process_text(text: str, operation: str = "upper") -> str:
    """
    Process text with various operations.

    Args:
        text: Text to process
        operation: Operation to perform (upper, lower, reverse)

    Returns:
        str: Processed text
    """
    if operation == "upper":
        return text.upper()
    elif operation == "lower":
        return text.lower()
    elif operation == "reverse":
        return text[::-1]
    else:
        return f"Error: Unknown operation {operation}"

def failing_tool() -> str:
    """A tool that always fails."""
    raise ValueError("This tool is designed to fail")

# Export tools
__all__ = ['calculate', 'get_time', 'process_text', 'failing_tool']

# Tool groups
__math__ = ['calculate']
__text__ = ['process_text']
__utility__ = ['get_time']
__test__ = ['failing_tool']
'''
        (tools_dir / "__init__.py").write_text(tools_content)
        return str(tools_dir)

    def test_full_tool_discovery_and_execution_flow(self, temp_tools_dir):
        """Test complete flow from discovery to execution."""
        # Discovery
        discovery = ToolDiscoveryService(temp_tools_dir)
        functions, groups = discovery.discover_tools()

        # Verify discovery worked
        assert "calculate" in functions
        assert "get_time" in functions
        assert "process_text" in functions
        assert "math" in groups
        assert "text" in groups

        # Schema generation
        schema_service = ToolSchemaService()
        descriptions = schema_service.get_tool_descriptions(functions)

        # Verify schemas
        assert "calculate" in descriptions
        calc_desc = descriptions["calculate"]
        # Description should be a string containing function description
        assert isinstance(calc_desc, str)
        assert "mathematical" in calc_desc.lower() or "expression" in calc_desc.lower()

        # Execution
        execution_service = ToolExecutionService(functions)

        # Test successful execution
        result = execution_service.execute_tool(
            "calculate", {"expression": "2 + 2"}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result.success
        assert result.result == "4"

        # Test execution with default parameter
        result = execution_service.execute_tool(
            "process_text", {"text": "hello"}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result.success
        assert result.result == "HELLO"

        # Test execution with explicit parameter
        result = execution_service.execute_tool(
            "process_text",
            {"text": "hello", "operation": "reverse"},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert result.success
        assert result.result == "olleh"

    def test_tool_group_execution(self, temp_tools_dir):
        """Test executing tools from a specific group."""
        discovery = ToolDiscoveryService(temp_tools_dir)
        functions, groups = discovery.discover_tools()

        # Get math group tools
        math_tools = groups["math"]
        assert "calculate" in math_tools

        # Create execution service with only math tools
        math_functions = {name: functions[name] for name in math_tools}
        execution_service = ToolExecutionService(math_functions)

        # Execute math tool
        result = execution_service.execute_tool(
            "calculate", {"expression": "10 * 5"}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result.success
        assert result.result == "50"

        # Verify non-math tools are not available
        result = execution_service.execute_tool(
            "get_time", {}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert not result.success
        assert "not found" in result.error_message.lower()

    def test_tool_error_handling_integration(self, temp_tools_dir):
        """Test error handling across the tool pipeline."""
        discovery = ToolDiscoveryService(temp_tools_dir)
        functions, groups = discovery.discover_tools()
        execution_service = ToolExecutionService(functions)

        # Test tool that raises exception
        result = execution_service.execute_tool(
            "failing_tool", {}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert not result.success
        assert "designed to fail" in result.error_message

        # Test tool with invalid input
        result = execution_service.execute_tool(
            "calculate",
            {"expression": "invalid math"},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert result.success  # Our calculate tool handles errors gracefully
        assert "Error:" in result.result

    def test_tool_confirmation_flow(self, temp_tools_dir):
        """Test tool execution with confirmation."""
        discovery = ToolDiscoveryService(temp_tools_dir)
        functions, groups = discovery.discover_tools()
        execution_service = ToolExecutionService(functions)

        # Test confirmation approved
        confirm_callback = Mock(return_value=True)
        result = execution_service.execute_tool(
            "get_time", {}, ToolExecutionPolicy.ALWAYS_CONFIRM, confirm_callback
        )
        assert result.success
        assert confirm_callback.called

        # Test confirmation denied
        confirm_callback = Mock(return_value=False)
        result = execution_service.execute_tool(
            "get_time", {}, ToolExecutionPolicy.ALWAYS_CONFIRM, confirm_callback
        )
        assert not result.success
        assert "denied by user" in result.error_message.lower()

    def test_session_tool_settings_integration(self, temp_tools_dir, tmp_path):
        """Test tool settings integration with chat sessions."""
        # Create a session with tool settings
        sessions_dir = tmp_path / "sessions"
        session = ChatSession("test-model", sessions_dir=str(sessions_dir))

        # Set up tool settings
        tool_settings = ToolSettings(
            tools=["calculate", "get_time"],
            tool_group=None,
            execution_policy=ToolExecutionPolicy.NEVER_CONFIRM,
        )
        session.metadata.tool_settings = tool_settings
        session.save_session()

        # Load session and verify settings
        loaded_session = ChatSession(
            "test-model", session_id=session.session_id, sessions_dir=str(sessions_dir)
        )
        loaded_settings = loaded_session.get_tool_settings()

        assert loaded_settings is not None
        assert loaded_settings.tools == ["calculate", "get_time"]
        assert loaded_settings.execution_policy == ToolExecutionPolicy.NEVER_CONFIRM

    def test_tool_reload_integration(self, temp_tools_dir):
        """Test tool reloading functionality."""
        discovery = ToolDiscoveryService(temp_tools_dir)

        # Initial discovery
        functions1, groups1 = discovery.discover_tools()
        assert "calculate" in functions1

        # Modify tools file
        tools_dir = Path(temp_tools_dir)
        updated_content = '''
def new_tool() -> str:
    """A new tool."""
    return "new"

def calculate(expression: str) -> str:
    """Updated calculate tool."""
    return f"Updated: {expression}"

__all__ = ['new_tool', 'calculate']
__new_group__ = ['new_tool']
'''
        (tools_dir / "__init__.py").write_text(updated_content)

        # Reload tools
        functions2, groups2 = discovery.reload_tools()
        assert "new_tool" in functions2
        assert "calculate" in functions2
        assert "new_group" in groups2

        # Test that new tool works
        execution_service = ToolExecutionService(functions2)
        result = execution_service.execute_tool(
            "new_tool", {}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result.success
        assert result.result == "new"

        # Test that updated tool works
        result = execution_service.execute_tool(
            "calculate", {"expression": "2+2"}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result.success
        assert "Updated:" in result.result

    def test_schema_service_integration(self, temp_tools_dir):
        """Test schema service with real tools."""
        discovery = ToolDiscoveryService(temp_tools_dir)
        functions, groups = discovery.discover_tools()
        schema_service = ToolSchemaService()

        # Generate schemas
        descriptions = schema_service.get_tool_descriptions(functions)

        # Test calculate tool schema
        calc_desc = descriptions.get("calculate")
        assert calc_desc is not None
        assert isinstance(calc_desc, str)

        # Test process_text tool schema
        text_desc = descriptions.get("process_text")
        assert text_desc is not None
        assert isinstance(text_desc, str)

        # Test tool with no parameters
        time_desc = descriptions.get("get_time")
        assert time_desc is not None
        assert isinstance(time_desc, str)

    def test_end_to_end_tool_call_simulation(self, temp_tools_dir):
        """Simulate an end-to-end tool call as would happen in chat."""
        # Set up services
        discovery = ToolDiscoveryService(temp_tools_dir)
        functions, groups = discovery.discover_tools()
        execution_service = ToolExecutionService(functions)

        # Simulate LLM requesting a tool call
        tool_call = {
            "function": {"name": "calculate", "arguments": {"expression": "15 + 27"}}
        }

        # Execute the tool call
        result = execution_service.execute_tool(
            tool_call["function"]["name"],
            tool_call["function"]["arguments"],
            ToolExecutionPolicy.NEVER_CONFIRM,
        )

        # Verify result
        assert result.success
        assert result.result == "42"
        assert result.tool_name == "calculate"

        # Simulate adding result to conversation
        tool_response = {
            "role": "tool",
            "tool_name": result.tool_name,
            "content": result.result,
        }

        assert tool_response["content"] == "42"

    def test_multiple_tool_execution_sequence(self, temp_tools_dir):
        """Test executing multiple tools in sequence."""
        discovery = ToolDiscoveryService(temp_tools_dir)
        functions, groups = discovery.discover_tools()
        execution_service = ToolExecutionService(functions)

        # Execute sequence of tools
        results = []

        # 1. Get current time
        result1 = execution_service.execute_tool(
            "get_time", {}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result1.success
        results.append(result1)

        # 2. Process some text
        result2 = execution_service.execute_tool(
            "process_text",
            {"text": "hello world", "operation": "upper"},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert result2.success
        assert result2.result == "HELLO WORLD"
        results.append(result2)

        # 3. Do a calculation
        result3 = execution_service.execute_tool(
            "calculate", {"expression": "100 - 42"}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result3.success
        assert result3.result == "58"
        results.append(result3)

        # Verify all results
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_tool_settings_persistence(self, temp_tools_dir, tmp_path):
        """Test that tool settings persist across session reloads."""
        sessions_dir = tmp_path / "sessions"

        # Create session with tool settings
        session = ChatSession("test-model", sessions_dir=str(sessions_dir))

        tool_settings = ToolSettings(
            tools=["calculate"],
            tool_group=None,
            execution_policy=ToolExecutionPolicy.ALWAYS_CONFIRM,
        )
        session.metadata.tool_settings = tool_settings
        session.save_session()

        # Load session in new instance
        new_session = ChatSession(
            "test-model", session_id=session.session_id, sessions_dir=str(sessions_dir)
        )

        # Verify settings persisted
        loaded_settings = new_session.get_tool_settings()
        assert loaded_settings is not None
        assert loaded_settings.tools == ["calculate"]
        assert loaded_settings.execution_policy == ToolExecutionPolicy.ALWAYS_CONFIRM

    def test_malformed_tool_directory_handling(self, tmp_path):
        """Test handling of malformed tool directories."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create malformed Python file
        (tools_dir / "__init__.py").write_text("invalid python syntax!!!")

        discovery = ToolDiscoveryService(str(tools_dir))
        functions, groups = discovery.discover_tools()

        # Should handle gracefully
        assert functions == {}
        assert groups == {}
