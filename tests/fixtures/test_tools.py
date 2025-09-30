"""Test tools for unit testing."""

def mock_successful_tool(arg1: str, arg2: int = 10) -> str:
    """
    A mock tool that always succeeds.

    Args:
        arg1: A string argument
        arg2: An integer argument with default

    Returns:
        str: A success message
    """
    return f"Success: {arg1} with {arg2}"

def mock_failing_tool() -> str:
    """A mock tool that always fails."""
    raise ValueError("This tool always fails")

def mock_no_docstring_tool():
    return "No docstring"

def mock_no_type_hints_tool(arg1, arg2):
    """Tool without type hints."""
    return f"{arg1} {arg2}"

def mock_complex_tool(data: dict, options: list = None) -> dict:
    """
    A tool that works with complex data types.

    Args:
        data: Dictionary of input data
        options: Optional list of configuration options

    Returns:
        dict: Processed data
    """
    if options is None:
        options = []

    return {
        "processed": True,
        "input_keys": list(data.keys()),
        "options_count": len(options),
        "result": "Complex processing complete"
    }

def mock_network_tool(url: str, timeout: int = 30) -> str:
    """
    Mock tool that simulates network operations.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        str: Mock response
    """
    if "error" in url:
        raise ConnectionError("Failed to connect")
    return f"Fetched data from {url} with timeout {timeout}"

def mock_file_tool(filename: str, mode: str = "read") -> str:
    """
    Mock tool for file operations.

    Args:
        filename: Name of the file
        mode: Operation mode ('read' or 'write')

    Returns:
        str: Operation result
    """
    if mode == "read":
        return f"Reading from {filename}"
    elif mode == "write":
        return f"Writing to {filename}"
    else:
        raise ValueError(f"Invalid mode: {mode}")

__all__ = [
    'mock_successful_tool',
    'mock_failing_tool',
    'mock_no_docstring_tool',
    'mock_no_type_hints_tool',
    'mock_complex_tool',
    'mock_network_tool',
    'mock_file_tool'
]

__test_group__ = ['mock_successful_tool', 'mock_failing_tool']
__complex_group__ = ['mock_complex_tool', 'mock_network_tool', 'mock_file_tool']
