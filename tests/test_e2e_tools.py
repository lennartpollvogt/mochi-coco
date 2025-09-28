import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import json

from mochi_coco.tools.discovery_service import ToolDiscoveryService
from mochi_coco.tools.execution_service import ToolExecutionService
from mochi_coco.tools.schema_service import ToolSchemaService
from mochi_coco.tools.config import ToolSettings, ToolExecutionPolicy
from mochi_coco.chat.session import ChatSession
from mochi_coco.commands.command_processor import CommandProcessor


@pytest.mark.integration
class TestToolsE2E:
    """End-to-end tests for tool functionality."""

    @pytest.fixture
    def complete_tools_setup(self, tmp_path):
        """Set up a complete tools environment for testing."""
        # Create tools directory
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create comprehensive test tools
        tools_content = '''
"""Complete test tools for E2E testing."""

def calculator(operation: str, a: float, b: float) -> str:
    """
    Perform basic arithmetic operations.

    Args:
        operation: The operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number

    Returns:
        str: Result of the calculation
    """
    try:
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return "Error: Division by zero"
            result = a / b
        else:
            return f"Error: Unknown operation {operation}"
        return str(int(result) if result == int(result) else result)
    except Exception as e:
        return f"Error: {e}"

def text_processor(text: str, action: str = "upper") -> str:
    """
    Process text with various actions.

    Args:
        text: Text to process
        action: Action to perform (upper, lower, reverse, count)

    Returns:
        str: Processed text or count
    """
    if action == "upper":
        return text.upper()
    elif action == "lower":
        return text.lower()
    elif action == "reverse":
        return text[::-1]
    elif action == "count":
        return str(len(text.split()))
    else:
        return f"Unknown action: {action}"

def file_info(filename: str) -> str:
    """
    Get information about a file.

    Args:
        filename: Name of the file to inspect

    Returns:
        str: File information
    """
    from pathlib import Path

    try:
        path = Path(filename)
        if not path.exists():
            return f"File {filename} does not exist"

        size = path.stat().st_size
        return f"File: {filename}, Size: {size} bytes, Type: {'Directory' if path.is_dir() else 'File'}"
    except Exception as e:
        return f"Error: {e}"

def failing_tool() -> str:
    """A tool that always fails for error testing."""
    raise RuntimeError("This tool is designed to fail")

def slow_tool() -> str:
    """A tool that simulates slow processing."""
    import time
    time.sleep(0.1)  # Short delay for testing
    return "Slow operation completed"

# Export individual tools
__all__ = [
    'calculator',
    'text_processor',
    'file_info',
    'failing_tool',
    'slow_tool'
]

# Define tool groups
__math__ = ['calculator']
__text__ = ['text_processor']
__system__ = ['file_info']
__test__ = ['failing_tool', 'slow_tool']
__basic__ = ['calculator', 'text_processor']
'''

        (tools_dir / "__init__.py").write_text(tools_content)

        # Create sessions directory
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        return {
            "tools_dir": str(tools_dir),
            "sessions_dir": str(sessions_dir),
            "tmp_path": tmp_path,
        }

    def test_complete_tool_discovery_flow(self, complete_tools_setup):
        """Test the complete tool discovery process."""
        tools_dir = complete_tools_setup["tools_dir"]

        # Initialize discovery service
        discovery = ToolDiscoveryService(tools_dir)

        # Discover tools
        functions, groups = discovery.discover_tools()

        # Verify all tools were discovered
        assert "calculator" in functions
        assert "text_processor" in functions
        assert "file_info" in functions
        assert "failing_tool" in functions
        assert "slow_tool" in functions

        # Verify groups were discovered
        assert "math" in groups
        assert "text" in groups
        assert "system" in groups
        assert "test" in groups
        assert "basic" in groups

        # Verify group contents
        assert "calculator" in groups["math"]
        assert "text_processor" in groups["text"]
        assert len(groups["basic"]) == 2

    def test_tool_schema_generation(self, complete_tools_setup):
        """Test schema generation for discovered tools."""
        tools_dir = complete_tools_setup["tools_dir"]

        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()

        schema_service = ToolSchemaService()
        descriptions = schema_service.get_tool_descriptions(functions)

        # Verify schemas were generated
        assert "calculator" in descriptions
        assert "text_processor" in descriptions

        # Check calculator schema
        calc_schema = descriptions["calculator"]
        assert "operation" in calc_schema
        assert "a" in calc_schema
        assert "b" in calc_schema

        # Check text processor schema (with default parameter)
        text_schema = descriptions["text_processor"]
        assert "text" in text_schema
        assert "action" in text_schema

    def test_tool_execution_success_cases(self, complete_tools_setup):
        """Test successful tool execution scenarios."""
        tools_dir = complete_tools_setup["tools_dir"]

        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()

        execution_service = ToolExecutionService(functions)

        # Test calculator tool
        result = execution_service.execute_tool(
            "calculator",
            {"operation": "add", "a": 5, "b": 3},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert result.success
        assert result.result == "8"

        # Test text processor with default parameter
        result = execution_service.execute_tool(
            "text_processor", {"text": "hello world"}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result.success
        assert result.result == "HELLO WORLD"

        # Test text processor with explicit parameter
        result = execution_service.execute_tool(
            "text_processor",
            {"text": "hello world", "action": "reverse"},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert result.success
        assert result.result == "dlrow olleh"

    def test_tool_execution_error_handling(self, complete_tools_setup):
        """Test error handling in tool execution."""
        tools_dir = complete_tools_setup["tools_dir"]

        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()

        execution_service = ToolExecutionService(functions)

        # Test division by zero
        result = execution_service.execute_tool(
            "calculator",
            {"operation": "divide", "a": 10, "b": 0},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert result.success  # Tool handles error gracefully
        assert "Division by zero" in result.result

        # Test unknown operation
        result = execution_service.execute_tool(
            "calculator",
            {"operation": "modulo", "a": 10, "b": 3},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert result.success  # Tool handles error gracefully
        assert "Unknown operation" in result.result

        # Test failing tool
        result = execution_service.execute_tool(
            "failing_tool", {}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert not result.success
        assert "designed to fail" in result.error_message

    def test_tool_confirmation_workflow(self, complete_tools_setup):
        """Test tool confirmation workflow."""
        tools_dir = complete_tools_setup["tools_dir"]

        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()

        execution_service = ToolExecutionService(functions)

        # Test confirmation approved
        confirm_callback = Mock(return_value=True)
        result = execution_service.execute_tool(
            "calculator",
            {"operation": "add", "a": 1, "b": 1},
            ToolExecutionPolicy.ALWAYS_CONFIRM,
            confirm_callback,
        )
        assert result.success
        assert confirm_callback.called
        confirm_callback.assert_called_once()

        # Test confirmation denied
        confirm_callback = Mock(return_value=False)
        result = execution_service.execute_tool(
            "calculator",
            {"operation": "add", "a": 1, "b": 1},
            ToolExecutionPolicy.ALWAYS_CONFIRM,
            confirm_callback,
        )
        assert not result.success
        assert "denied by user" in result.error_message.lower()

    def test_session_tool_settings_persistence(self, complete_tools_setup):
        """Test tool settings persistence in chat sessions."""
        sessions_dir = complete_tools_setup["sessions_dir"]

        # Create session with tool settings
        session = ChatSession("test-model", sessions_dir=sessions_dir)

        # Configure individual tools
        tool_settings = ToolSettings(
            tools=["calculator", "text_processor"],
            tool_group=None,
            execution_policy=ToolExecutionPolicy.ALWAYS_CONFIRM,
        )
        session.metadata.tool_settings = tool_settings
        session.save_session()

        # Load session and verify settings
        loaded_session = ChatSession(
            "test-model", session_id=session.session_id, sessions_dir=sessions_dir
        )
        loaded_settings = loaded_session.get_tool_settings()

        assert loaded_settings is not None
        assert loaded_settings.tools == ["calculator", "text_processor"]
        assert loaded_settings.execution_policy == ToolExecutionPolicy.ALWAYS_CONFIRM
        assert loaded_settings.tool_group is None

        # Test tool group settings
        session2 = ChatSession("test-model", sessions_dir=sessions_dir)
        group_settings = ToolSettings(
            tools=[],
            tool_group="math",
            execution_policy=ToolExecutionPolicy.NEVER_CONFIRM,
        )
        session2.metadata.tool_settings = group_settings
        session2.save_session()

        # Load and verify group settings
        loaded_session2 = ChatSession(
            "test-model", session_id=session2.session_id, sessions_dir=sessions_dir
        )
        loaded_group_settings = loaded_session2.get_tool_settings()

        assert loaded_group_settings.tool_group == "math"
        assert loaded_group_settings.tools == []
        assert (
            loaded_group_settings.execution_policy == ToolExecutionPolicy.NEVER_CONFIRM
        )

    def test_tool_reload_functionality(self, complete_tools_setup):
        """Test tool reloading functionality."""
        tools_dir = Path(complete_tools_setup["tools_dir"])

        discovery = ToolDiscoveryService(str(tools_dir))

        # Initial discovery
        functions1, groups1 = discovery.discover_tools()
        assert "calculator" in functions1
        assert (
            len(functions1) == 5
        )  # calculator, text_processor, file_info, failing_tool, slow_tool

        # Modify tools file to add new tool
        updated_content = '''
"""Updated test tools."""

def calculator(operation: str, a: float, b: float) -> str:
    """Updated calculator tool."""
    return f"Updated calc: {operation}({a}, {b})"

def new_amazing_tool() -> str:
    """A new tool added during reload."""
    return "This is a new tool!"

__all__ = ['calculator', 'new_amazing_tool']
__updated__ = ['new_amazing_tool']
'''
        (tools_dir / "__init__.py").write_text(updated_content)

        # Reload tools
        functions2, groups2 = discovery.reload_tools()

        # Verify changes
        assert "calculator" in functions2
        assert "new_amazing_tool" in functions2
        assert len(functions2) == 2  # Only the new tools
        assert "updated" in groups2

        # Test new tool execution
        execution_service = ToolExecutionService(functions2)
        result = execution_service.execute_tool(
            "new_amazing_tool", {}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert result.success
        assert "new tool" in result.result

    def test_tool_group_execution_workflow(self, complete_tools_setup):
        """Test executing tools from specific groups."""
        tools_dir = complete_tools_setup["tools_dir"]

        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()

        # Test math group
        math_tools = groups["math"]
        assert "calculator" in math_tools

        math_functions = {name: functions[name] for name in math_tools}
        math_execution_service = ToolExecutionService(math_functions)

        # Execute math tool
        result = math_execution_service.execute_tool(
            "calculator",
            {"operation": "multiply", "a": 6, "b": 7},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert result.success
        assert result.result == "42"

        # Verify non-math tools are not available
        result = math_execution_service.execute_tool(
            "text_processor", {"text": "test"}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert not result.success
        assert "not found" in result.error_message.lower()

    @patch("mochi_coco.ollama.client.Client")
    def test_simulated_chat_with_tools(self, mock_client, complete_tools_setup):
        """Simulate a complete chat session with tool usage."""
        tools_dir = complete_tools_setup["tools_dir"]
        sessions_dir = complete_tools_setup["sessions_dir"]

        # Set up tools
        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()
        execution_service = ToolExecutionService(functions)

        # Create session with tools enabled
        session = ChatSession("test-model", sessions_dir=sessions_dir)
        tool_settings = ToolSettings(
            tools=["calculator", "text_processor"],
            execution_policy=ToolExecutionPolicy.NEVER_CONFIRM,
        )
        session.metadata.tool_settings = tool_settings

        # Add user message
        session.add_user_message("Calculate 15 + 27 and then make the result uppercase")

        # Mock LLM response with tool calls
        mock_tool_calls = [
            {
                "function": {
                    "name": "calculator",
                    "arguments": {"operation": "add", "a": 15, "b": 27},
                }
            }
        ]

        # Execute the first tool call
        tool_call = mock_tool_calls[0]
        result1 = execution_service.execute_tool(
            tool_call["function"]["name"],
            tool_call["function"]["arguments"],
            tool_settings.execution_policy,
        )

        assert result1.success
        assert result1.result == "42"

        # Simulate second tool call based on first result
        result2 = execution_service.execute_tool(
            "text_processor",
            {"text": result1.result, "action": "upper"},
            tool_settings.execution_policy,
        )

        assert result2.success
        assert result2.result == "42"  # Numbers don't change case, but no error

    def test_command_processor_tool_commands(self, complete_tools_setup):
        """Test command processor tool-related commands."""
        sessions_dir = complete_tools_setup["sessions_dir"]

        # Mock dependencies
        mock_model_selector = Mock()
        mock_renderer_manager = Mock()

        # Create command processor
        processor = CommandProcessor(mock_model_selector, mock_renderer_manager)

        # Create session
        session = ChatSession("test-model", sessions_dir=sessions_dir)

        # Test tool availability detection
        with patch.object(Path, "exists", return_value=True):
            with patch.object(processor, "_are_tools_available", return_value=True):
                command_map = processor._build_dynamic_command_map(session)
                assert "/tools" in command_map
                assert "/5" in command_map or "/6" in command_map  # Dynamic numbering

    def test_multiple_tool_execution_sequence(self, complete_tools_setup):
        """Test executing multiple tools in a realistic sequence."""
        tools_dir = complete_tools_setup["tools_dir"]

        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()
        execution_service = ToolExecutionService(functions)

        # Sequence 1: Math calculation
        calc_result = execution_service.execute_tool(
            "calculator",
            {"operation": "multiply", "a": 8, "b": 9},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert calc_result.success
        assert calc_result.result == "72"

        # Sequence 2: Process the result as text
        text_result = execution_service.execute_tool(
            "text_processor",
            {"text": f"The result is {calc_result.result}", "action": "upper"},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert text_result.success
        assert "THE RESULT IS 72" == text_result.result

        # Sequence 3: Count words in the processed text
        count_result = execution_service.execute_tool(
            "text_processor",
            {"text": text_result.result, "action": "count"},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert count_result.success
        assert count_result.result == "4"  # "THE RESULT IS 72" has 4 words

    def test_error_recovery_workflow(self, complete_tools_setup):
        """Test error recovery in tool execution workflow."""
        tools_dir = complete_tools_setup["tools_dir"]

        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()
        execution_service = ToolExecutionService(functions)

        # Start with a failing operation
        failing_result = execution_service.execute_tool(
            "calculator",
            {"operation": "divide", "a": 10, "b": 0},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert failing_result.success  # Tool handles error gracefully
        assert "Division by zero" in failing_result.result

        # Continue with a successful operation
        success_result = execution_service.execute_tool(
            "calculator",
            {"operation": "divide", "a": 10, "b": 2},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert success_result.success
        assert success_result.result == "5"

        # Test with completely failing tool
        exception_result = execution_service.execute_tool(
            "failing_tool", {}, ToolExecutionPolicy.NEVER_CONFIRM
        )
        assert not exception_result.success

        # Verify we can still execute other tools after a failure
        recovery_result = execution_service.execute_tool(
            "text_processor",
            {"text": "recovery test"},
            ToolExecutionPolicy.NEVER_CONFIRM,
        )
        assert recovery_result.success
        assert recovery_result.result == "RECOVERY TEST"

    def test_session_metadata_migration(self, complete_tools_setup):
        """Test session metadata migration with tool settings."""
        sessions_dir = complete_tools_setup["sessions_dir"]

        # Create an old-style session manually (without format_version)
        old_session_data = {
            "metadata": {
                "session_id": "test123",
                "model": "test-model",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "message_count": 0,
                # No format_version or tool_settings
            },
            "messages": [],
        }

        session_file = Path(sessions_dir) / "test123.json"
        with open(session_file, "w") as f:
            json.dump(old_session_data, f)

        # Load the session (should trigger migration)
        session = ChatSession(
            "test-model", session_id="test123", sessions_dir=sessions_dir
        )

        # Verify migration occurred
        assert hasattr(session.metadata, "format_version")
        assert session.metadata.format_version == "1.1"
        assert hasattr(session.metadata, "tool_settings")
        assert session.metadata.tool_settings is None  # Default for migrated sessions

    def test_concurrent_tool_execution(self, complete_tools_setup):
        """Test that tool execution works correctly with multiple requests."""
        tools_dir = complete_tools_setup["tools_dir"]

        discovery = ToolDiscoveryService(tools_dir)
        functions, groups = discovery.discover_tools()
        execution_service = ToolExecutionService(functions)

        # Execute multiple tools "simultaneously" (in sequence for testing)
        results = []

        # Different calculations
        test_cases = [
            ("add", 1, 2, "3"),
            ("subtract", 10, 3, "7"),
            ("multiply", 4, 5, "20"),
            ("divide", 15, 3, "5"),
        ]

        for operation, a, b, expected in test_cases:
            result = execution_service.execute_tool(
                "calculator",
                {"operation": operation, "a": a, "b": b},
                ToolExecutionPolicy.NEVER_CONFIRM,
            )
            assert result.success
            assert result.result == expected
            results.append(result)

        # Verify all executions were successful
        assert len(results) == 4
        assert all(r.success for r in results)

        # Verify execution times are recorded
        assert all(r.execution_time > 0 for r in results)

        # Verify metadata is correct
        for i, (operation, a, b, expected) in enumerate(test_cases):
            result = results[i]
            assert result.tool_name == "calculator"
            # Note: ToolExecutionResult doesn't store arguments in current implementation
