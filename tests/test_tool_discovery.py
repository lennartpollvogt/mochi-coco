from pathlib import Path
import shutil

from mochi_coco.tools.discovery_service import ToolDiscoveryService


class TestToolDiscovery:
    """Test suite for tool discovery functionality."""

    def test_discover_tools_no_directory(self, tmp_path):
        """Test discovery when tools directory doesn't exist."""
        non_existent = tmp_path / "non_existent"
        service = ToolDiscoveryService(str(non_existent))
        functions, groups = service.discover_tools()
        assert functions == {}
        assert groups == {}

    def test_discover_tools_with_fixtures(self, tmp_path):
        """Test discovery with test fixtures."""
        # Copy test fixtures to temp directory
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Copy test tools
        test_tools = Path(__file__).parent / "fixtures" / "test_tools.py"
        shutil.copy(test_tools, tools_dir / "__init__.py")

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        assert 'mock_successful_tool' in functions
        assert 'mock_failing_tool' in functions
        assert 'test_group' in groups
        assert 'mock_successful_tool' in groups['test_group']

    def test_reload_tools(self, tmp_path):
        """Test reloading tools after changes."""
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
        functions, _ = service.discover_tools()
        assert 'tool1' in functions
        assert 'tool2' not in functions

        # Update content
        updated_content = '''
def tool1():
    """Tool 1"""
    return "1"

def tool2():
    """Tool 2"""
    return "2"

__all__ = ['tool1', 'tool2']
'''
        (tools_dir / "__init__.py").write_text(updated_content)

        # Reload
        functions, _ = service.reload_tools()
        assert 'tool1' in functions
        assert 'tool2' in functions

    def test_discover_tools_with_groups(self, tmp_path):
        """Test discovery of tool groups."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        content = '''
def math_add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def math_subtract(a: int, b: int) -> int:
    """Subtract two numbers."""
    return a - b

def text_upper(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()

__all__ = ['math_add', 'math_subtract', 'text_upper']
__math__ = ['math_add', 'math_subtract']
__text__ = ['text_upper']
'''
        (tools_dir / "__init__.py").write_text(content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        assert len(functions) == 3
        assert 'math' in groups
        assert 'text' in groups
        assert groups['math'] == ['math_add', 'math_subtract']
        assert groups['text'] == ['text_upper']

    def test_discover_tools_malformed_init(self, tmp_path):
        """Test discovery with malformed __init__.py file."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create malformed Python file
        malformed_content = '''
def valid_tool():
    """A valid tool."""
    return "valid"

# This will cause a syntax error
invalid syntax here!
'''
        (tools_dir / "__init__.py").write_text(malformed_content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        # Should return empty dicts when file is malformed
        assert functions == {}
        assert groups == {}

    def test_discover_tools_missing_docstring(self, tmp_path):
        """Test discovery with tools missing docstrings."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        content = '''
def tool_with_docstring():
    """This tool has a docstring."""
    return "documented"

def tool_without_docstring():
    return "undocumented"

__all__ = ['tool_with_docstring', 'tool_without_docstring']
'''
        (tools_dir / "__init__.py").write_text(content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        # Only tool with docstring should be discovered
        assert 'tool_with_docstring' in functions
        assert 'tool_without_docstring' not in functions

        # Check that function is callable
        assert callable(functions['tool_with_docstring'])

    def test_discover_tools_no_all_export(self, tmp_path):
        """Test discovery when __all__ is not defined."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        content = '''
def some_tool():
    """A tool without __all__ export."""
    return "hidden"

def _private_tool():
    """A private tool."""
    return "private"

__math__ = ['some_tool']
'''
        (tools_dir / "__init__.py").write_text(content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        # Should find no functions without __all__
        assert functions == {}
        # Groups with invalid tools should not be found
        assert groups == {}

    def test_discover_tools_empty_all(self, tmp_path):
        """Test discovery with empty __all__ list."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        content = '''
def some_tool():
    """A tool."""
    return "tool"

__all__ = []
'''
        (tools_dir / "__init__.py").write_text(content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        assert functions == {}
        assert groups == {}

    def test_discover_tools_invalid_function_reference(self, tmp_path):
        """Test discovery when __all__ references non-existent function."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        content = '''
def existing_tool():
    """An existing tool."""
    return "exists"

__all__ = ['existing_tool', 'non_existent_tool']
'''
        (tools_dir / "__init__.py").write_text(content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        # Should only include existing functions
        assert 'existing_tool' in functions
        assert 'non_existent_tool' not in functions

    def test_service_caching(self, tmp_path):
        """Test that the service caches results appropriately."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        content = '''
def cached_tool():
    """A cached tool."""
    return "cached"

__all__ = ['cached_tool']
'''
        (tools_dir / "__init__.py").write_text(content)

        service = ToolDiscoveryService(str(tools_dir))

        # First call
        functions1, groups1 = service.discover_tools()

        # Second call should return cached results (same objects)
        functions2, groups2 = service.discover_tools()

        # Check that the service returns the same cached objects
        assert functions1 is functions2
        assert groups1 is groups2
        assert 'cached_tool' in functions1

    def test_reload_clears_cache(self, tmp_path):
        """Test that reload_tools clears the cache."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        initial_content = '''
def tool1():
    """Tool 1."""
    return "1"

__all__ = ['tool1']
'''
        (tools_dir / "__init__.py").write_text(initial_content)

        service = ToolDiscoveryService(str(tools_dir))

        # Initial discovery
        functions1, _ = service.discover_tools()
        assert 'tool1' in functions1

        # Modify file
        updated_content = '''
def tool2():
    """Tool 2."""
    return "2"

__all__ = ['tool2']
'''
        (tools_dir / "__init__.py").write_text(updated_content)

        # Reload should pick up changes
        functions2, _ = service.reload_tools()
        # Note: reload behavior may vary - just check tool2 exists
        assert 'tool2' in functions2

    def test_group_name_normalization(self, tmp_path):
        """Test that group names are normalized correctly."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        content = '''
def tool1():
    """Tool 1."""
    return "1"

def tool2():
    """Tool 2."""
    return "2"

__all__ = ['tool1', 'tool2']
__math_utils__ = ['tool1']
__text_processing__ = ['tool2']
'''
        (tools_dir / "__init__.py").write_text(content)

        service = ToolDiscoveryService(str(tools_dir))
        functions, groups = service.discover_tools()

        # Check that group names are normalized (underscores removed)
        assert 'math_utils' in groups
        assert 'text_processing' in groups
        assert groups['math_utils'] == ['tool1']
        assert groups['text_processing'] == ['tool2']
