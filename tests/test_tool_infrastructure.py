"""
Unit tests for tool infrastructure components.

Tests the tool discovery service, schema service, configuration, and UI components
that form the foundation of the custom tools feature.
"""

from unittest.mock import Mock, patch

from mochi_coco.tools.discovery_service import ToolDiscoveryService
from mochi_coco.tools.schema_service import ToolSchemaService
from mochi_coco.tools.config import ToolSettings, ToolExecutionPolicy
from mochi_coco.ui.tool_selection_ui import ToolSelectionUI


class TestToolDiscovery:
    """Tests for ToolDiscoveryService"""

    def test_create_tools_dir_if_missing(self, tmp_path):
        """Test that tools directory is created if missing."""
        tools_dir = tmp_path / "tools"
        service = ToolDiscoveryService(str(tools_dir))

        functions, groups = service.discover_tools()

        assert tools_dir.exists()
        assert (tools_dir / "__init__.py").exists()
        assert functions == {}
        assert groups == {}

    def test_discover_valid_tools(self, tmp_path):
        """Test discovery of valid tool functions."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        init_content = '''
def tool1(x: int) -> str:
    """Tool 1 description"""
    return str(x)

def tool2() -> str:
    """Tool 2 description"""
    return "result"

__all__ = ['tool1', 'tool2']
'''
        (tools_dir / "__init__.py").write_text(init_content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        assert "tool1" in functions
        assert "tool2" in functions
        assert callable(functions["tool1"])
        assert callable(functions["tool2"])

    def test_discover_tool_groups(self, tmp_path):
        """Test discovery of tool groups."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        init_content = '''
def tool1():
    """Tool 1"""
    return "1"

def tool2():
    """Tool 2"""
    return "2"

__all__ = ['tool1', 'tool2']
__group1__ = ['tool1']
__group2__ = ['tool1', 'tool2']
'''
        (tools_dir / "__init__.py").write_text(init_content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        assert "group1" in groups
        assert "group2" in groups
        assert "tool1" in groups["group1"]
        assert "tool1" in groups["group2"]
        assert "tool2" in groups["group2"]

    def test_invalid_tool_without_docstring_rejected(self, tmp_path):
        """Test that functions without docstrings are rejected."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        init_content = '''
def valid_tool():
    """This has a docstring"""
    return "valid"

def invalid_tool():
    return "invalid"

__all__ = ['valid_tool', 'invalid_tool']
'''
        (tools_dir / "__init__.py").write_text(init_content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        assert "valid_tool" in functions
        assert "invalid_tool" not in functions

    def test_tool_group_with_invalid_tool_reference(self, tmp_path):
        """Test that tool groups with invalid references are handled correctly."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        init_content = '''
def tool1():
    """Tool 1"""
    return "1"

__all__ = ['tool1']
__group1__ = ['tool1', 'nonexistent_tool']
'''
        (tools_dir / "__init__.py").write_text(init_content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        assert "group1" in groups
        assert groups["group1"] == ["tool1"]  # Only valid tool included

    def test_reload_tools(self, tmp_path):
        """Test that tools can be reloaded."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Initial content
        init_content = '''
def tool1():
    """Tool 1"""
    return "1"

__all__ = ['tool1']
'''
        (tools_dir / "__init__.py").write_text(init_content)

        service = ToolDiscoveryService(str(tools_dir))
        functions1, groups1 = service.discover_tools()

        assert "tool1" in functions1
        assert len(functions1) == 1

        # Update content
        new_content = '''
def tool1():
    """Tool 1"""
    return "1"

def tool2():
    """Tool 2"""
    return "2"

__all__ = ['tool1', 'tool2']
'''
        (tools_dir / "__init__.py").write_text(new_content)

        # Reload should pick up changes
        functions2, groups2 = service.reload_tools()

        assert "tool1" in functions2
        assert "tool2" in functions2
        assert len(functions2) == 2

    def test_module_loading_error_handling(self, tmp_path):
        """Test handling of module loading errors."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create invalid Python file
        (tools_dir / "__init__.py").write_text("invalid python syntax !!!")

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        assert functions == {}
        assert groups == {}


class TestToolSchema:
    """Tests for ToolSchemaService"""

    @patch("mochi_coco.tools.schema_service.convert_function_to_tool")
    def test_convert_function_to_tool(self, mock_convert):
        """Test conversion of function to Tool schema."""

        def test_func(x: int, y: str = "default") -> str:
            """
            Test function.

            Args:
                x: An integer
                y: A string with default

            Returns:
                str: A result
            """
            return f"{x} {y}"

        mock_tool = Mock()
        mock_tool.function.name = "test_func"
        mock_convert.return_value = mock_tool

        service = ToolSchemaService()
        tools = service.convert_functions_to_tools({"test_func": test_func})

        assert "test_func" in tools
        assert tools["test_func"] == mock_tool
        mock_convert.assert_called_once_with(test_func)

    @patch("mochi_coco.tools.schema_service.convert_function_to_tool")
    def test_caching(self, mock_convert):
        """Test that tool conversion is cached."""

        def test_func():
            """Test"""
            return "test"

        mock_tool = Mock()
        mock_convert.return_value = mock_tool

        service = ToolSchemaService()

        # Convert twice
        tools1 = service.convert_functions_to_tools({"test": test_func})
        tools2 = service.convert_functions_to_tools({"test": test_func})

        # Should return same cached object
        assert tools1["test"] is tools2["test"]
        # Should only call convert once due to caching
        mock_convert.assert_called_once()

    @patch("mochi_coco.tools.schema_service.convert_function_to_tool")
    def test_conversion_error_handling(self, mock_convert):
        """Test handling of conversion errors."""

        def test_func():
            """Test"""
            return "test"

        mock_convert.side_effect = Exception("Conversion failed")

        service = ToolSchemaService()
        tools = service.convert_functions_to_tools({"test": test_func})

        assert tools == {}  # Should be empty due to error

    def test_clear_cache(self):
        """Test that cache can be cleared."""
        service = ToolSchemaService()
        service._tool_cache["test"] = Mock()

        assert service._tool_cache
        service.clear_cache()
        assert not service._tool_cache

    def test_get_tool_descriptions(self):
        """Test extraction of tool descriptions from docstrings."""

        def tool_with_desc():
            """This is a tool description."""
            return "result"

        def tool_without_desc():
            return "result"

        service = ToolSchemaService()
        descriptions = service.get_tool_descriptions(
            {"with_desc": tool_with_desc, "without_desc": tool_without_desc}
        )

        assert "with_desc" in descriptions
        assert "without_desc" in descriptions
        assert descriptions["without_desc"] == "Function without_desc"

    @patch("mochi_coco.tools.schema_service._parse_docstring")
    def test_get_tool_descriptions_with_parsing_error(self, mock_parse):
        """Test handling of docstring parsing errors."""

        def test_func():
            """Test docstring"""
            return "result"

        mock_parse.side_effect = Exception("Parse error")

        service = ToolSchemaService()
        descriptions = service.get_tool_descriptions({"test": test_func})

        assert descriptions["test"] == "Function test"


class TestToolConfig:
    """Tests for ToolSettings and ToolExecutionPolicy"""

    def test_tool_settings_defaults(self):
        """Test default tool settings."""
        settings = ToolSettings()

        assert settings.tools == []
        assert settings.tool_group is None
        assert settings.execution_policy == ToolExecutionPolicy.ALWAYS_CONFIRM
        assert settings.confirmation_necessary

    def test_backward_compatibility_property(self):
        """Test backward compatibility property."""
        settings_confirm = ToolSettings(
            execution_policy=ToolExecutionPolicy.ALWAYS_CONFIRM
        )
        settings_no_confirm = ToolSettings(
            execution_policy=ToolExecutionPolicy.NEVER_CONFIRM
        )

        assert settings_confirm.confirmation_necessary
        assert not settings_no_confirm.confirmation_necessary

    def test_is_enabled(self):
        """Test tool enablement detection."""
        empty_settings = ToolSettings()
        tools_settings = ToolSettings(tools=["tool1"])
        group_settings = ToolSettings(tool_group="group1")

        assert not empty_settings.is_enabled()
        assert tools_settings.is_enabled()
        assert group_settings.is_enabled()

    def test_get_active_tools_from_individual_tools(self):
        """Test getting active tools from individual selection."""
        settings = ToolSettings(tools=["tool1", "tool2"])
        all_tools = {"tool1": Mock(), "tool2": Mock(), "tool3": Mock()}
        groups = {"group1": ["tool1"]}

        active = settings.get_active_tools(all_tools, groups)
        assert active == ["tool1", "tool2"]

    def test_get_active_tools_from_group(self):
        """Test getting active tools from a group."""
        settings = ToolSettings(tool_group="group1")
        all_tools = {"tool1": Mock(), "tool2": Mock()}
        groups = {"group1": ["tool1", "tool2"]}

        active = settings.get_active_tools(all_tools, groups)
        assert active == ["tool1", "tool2"]

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        settings = ToolSettings(
            tools=["tool1"],
            tool_group="group1",
            execution_policy=ToolExecutionPolicy.NEVER_CONFIRM,
        )

        data = settings.to_dict()

        assert data == {
            "tools": ["tool1"],
            "tool_group": "group1",
            "execution_policy": "never_confirm",
        }

    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        data = {
            "tools": ["tool1"],
            "tool_group": "group1",
            "execution_policy": "never_confirm",
        }

        settings = ToolSettings.from_dict(data)

        assert settings.tools == ["tool1"]
        assert settings.tool_group == "group1"
        assert settings.execution_policy == ToolExecutionPolicy.NEVER_CONFIRM

    def test_backward_compatibility_from_dict(self):
        """Test backward compatibility with old confirmation_necessary field."""
        old_data_confirm = {"tools": ["tool1"], "confirmation_necessary": True}

        old_data_no_confirm = {"tools": ["tool1"], "confirmation_necessary": False}

        settings_confirm = ToolSettings.from_dict(old_data_confirm)
        settings_no_confirm = ToolSettings.from_dict(old_data_no_confirm)

        assert settings_confirm.execution_policy == ToolExecutionPolicy.ALWAYS_CONFIRM
        assert settings_no_confirm.execution_policy == ToolExecutionPolicy.NEVER_CONFIRM


class TestToolSelectionUI:
    """Tests for ToolSelectionUI"""

    def test_ui_initialization(self):
        """Test UI component initialization."""
        ui = ToolSelectionUI()

        assert ui.console is not None
        assert "primary" in ui.colors
        assert "secondary" in ui.colors

    @patch("mochi_coco.ui.tool_selection_ui.Console")
    def test_display_tool_selection_menu(self, mock_console_class):
        """Test displaying the tool selection menu."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        ui = ToolSelectionUI()
        individual_tools = {"tool1": "Description 1", "tool2": "Description 2"}
        tool_groups = {"group1": ["tool1"]}

        ui.display_tool_selection_menu(individual_tools, tool_groups)

        # Should have called print to display the menu
        mock_console.print.assert_called()

    @patch("mochi_coco.ui.user_interaction.UserInteraction")
    def test_get_tool_selection_quit(self, mock_user_interaction_class):
        """Test quitting tool selection."""
        mock_user_interaction = Mock()
        mock_user_interaction.get_user_input.return_value = "q"
        mock_user_interaction_class.return_value = mock_user_interaction

        ui = ToolSelectionUI()
        result = ui.get_tool_selection(2, 1)

        assert result is None

    @patch("mochi_coco.ui.user_interaction.UserInteraction")
    def test_get_tool_selection_none(self, mock_user_interaction_class):
        """Test clearing tool selection."""
        mock_user_interaction = Mock()
        mock_user_interaction.get_user_input.return_value = "none"
        mock_user_interaction_class.return_value = mock_user_interaction

        ui = ToolSelectionUI()
        result = ui.get_tool_selection(2, 1)

        assert result == ([], False, None)

    @patch("mochi_coco.ui.user_interaction.UserInteraction")
    def test_get_tool_selection_reload(self, mock_user_interaction_class):
        """Test reload request."""
        mock_user_interaction = Mock()
        mock_user_interaction.get_user_input.return_value = "reload"
        mock_user_interaction_class.return_value = mock_user_interaction

        ui = ToolSelectionUI()
        result = ui.get_tool_selection(2, 1)

        assert result == ([], False, "reload")

    @patch("mochi_coco.ui.user_interaction.UserInteraction")
    def test_get_tool_selection_keep_current(self, mock_user_interaction_class):
        """Test keeping current selection."""
        mock_user_interaction = Mock()
        mock_user_interaction.get_user_input.return_value = ""
        mock_user_interaction_class.return_value = mock_user_interaction

        ui = ToolSelectionUI()
        result = ui.get_tool_selection(2, 1)

        assert result == ([], False, "keep")

    @patch("mochi_coco.ui.user_interaction.UserInteraction")
    def test_get_tool_selection_group_selection(self, mock_user_interaction_class):
        """Test group selection by letter."""
        mock_user_interaction = Mock()
        mock_user_interaction.get_user_input.return_value = "a"
        mock_user_interaction_class.return_value = mock_user_interaction

        ui = ToolSelectionUI()
        result = ui.get_tool_selection(2, 1)

        assert result == ([0], True, None)

    @patch("mochi_coco.ui.user_interaction.UserInteraction")
    def test_get_tool_selection_individual_tools(self, mock_user_interaction_class):
        """Test individual tool selection by numbers."""
        mock_user_interaction = Mock()
        mock_user_interaction.get_user_input.return_value = "1,3"
        mock_user_interaction_class.return_value = mock_user_interaction

        ui = ToolSelectionUI()
        result = ui.get_tool_selection(3, 0)

        assert result == ([0, 2], False, None)  # 0-based indices

    @patch("mochi_coco.ui.user_interaction.UserInteraction")
    def test_get_tool_selection_range(self, mock_user_interaction_class):
        """Test tool selection by range."""
        mock_user_interaction = Mock()
        mock_user_interaction.get_user_input.return_value = "1-3"
        mock_user_interaction_class.return_value = mock_user_interaction

        ui = ToolSelectionUI()
        result = ui.get_tool_selection(3, 0)

        assert result == ([0, 1, 2], False, None)  # 0-based indices

    @patch("mochi_coco.ui.user_interaction.UserInteraction")
    @patch("mochi_coco.ui.tool_selection_ui.Console")
    def test_get_tool_selection_invalid_input_retry(
        self, mock_console_class, mock_user_interaction_class
    ):
        """Test retry on invalid input."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_user_interaction = Mock()
        # First return invalid, then valid input
        mock_user_interaction.get_user_input.side_effect = ["invalid", "1"]
        mock_user_interaction_class.return_value = mock_user_interaction

        ui = ToolSelectionUI()
        result = ui.get_tool_selection(2, 0)

        # Should eventually succeed with valid input
        assert result == ([0], False, None)
        # Should have shown error message
        mock_console.print.assert_called()
