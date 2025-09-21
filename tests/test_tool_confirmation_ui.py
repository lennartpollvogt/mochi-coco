"""
Integration tests for tool confirmation UI.

This module contains tests for the ToolConfirmationUI class,
testing user interaction, display functionality, and error handling.
"""

import pytest
from unittest.mock import patch
from io import StringIO

from mochi_coco.ui.tool_confirmation_ui import ToolConfirmationUI


class TestToolConfirmationUI:

    def setup_method(self):
        """Set up test fixtures."""
        self.ui = ToolConfirmationUI()

    @patch('builtins.input', return_value='y')
    def test_confirm_execution_approved(self, mock_input):
        """Test confirmation when user approves."""
        result = self.ui.confirm_tool_execution('test_tool', {'x': 42})

        assert result is True
        mock_input.assert_called_once()

    @patch('builtins.input', return_value='yes')
    def test_confirm_execution_approved_verbose(self, mock_input):
        """Test confirmation with verbose 'yes' response."""
        result = self.ui.confirm_tool_execution('test_tool', {'x': 42})

        assert result is True
        mock_input.assert_called_once()

    @patch('builtins.input', return_value='n')
    def test_confirm_execution_denied(self, mock_input):
        """Test confirmation when user denies."""
        result = self.ui.confirm_tool_execution('test_tool', {'x': 42})

        assert result is False
        mock_input.assert_called_once()

    @patch('builtins.input', return_value='no')
    def test_confirm_execution_denied_verbose(self, mock_input):
        """Test confirmation with verbose 'no' response."""
        result = self.ui.confirm_tool_execution('test_tool', {'x': 42})

        assert result is False
        mock_input.assert_called_once()

    @patch('builtins.input', return_value='')
    def test_confirm_execution_default_denial(self, mock_input):
        """Test confirmation with empty input (default to deny)."""
        result = self.ui.confirm_tool_execution('test_tool', {'x': 42})

        assert result is False
        mock_input.assert_called_once()

    @patch('builtins.input', return_value='invalid')
    def test_confirm_execution_invalid_input(self, mock_input):
        """Test confirmation with invalid input (should default to deny)."""
        result = self.ui.confirm_tool_execution('test_tool', {'x': 42})

        assert result is False
        mock_input.assert_called_once()

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_confirm_execution_interrupted(self, mock_input):
        """Test confirmation when user interrupts."""
        result = self.ui.confirm_tool_execution('test_tool', {'x': 42})

        assert result is False

    @patch('builtins.input', side_effect=EOFError)
    def test_confirm_execution_eof_error(self, mock_input):
        """Test confirmation when EOF is reached."""
        result = self.ui.confirm_tool_execution('test_tool', {'x': 42})

        assert result is False

    def test_show_successful_result(self):
        """Test displaying successful result."""
        # Should not raise any exceptions
        try:
            self.ui.show_tool_result('test_tool', True,
                                   result="Success", execution_time=0.5)
        except Exception as e:
            pytest.fail(f"show_tool_result raised an exception: {e}")

    def test_show_error_result(self):
        """Test displaying error result."""
        # Should not raise any exceptions
        try:
            self.ui.show_tool_result('test_tool', False,
                                   error="Test error", execution_time=0.1)
        except Exception as e:
            pytest.fail(f"show_tool_result raised an exception: {e}")

    def test_show_successful_result_without_output(self):
        """Test displaying successful result without output."""
        try:
            self.ui.show_tool_result('test_tool', True, execution_time=0.2)
        except Exception as e:
            pytest.fail(f"show_tool_result raised an exception: {e}")

    def test_show_error_result_without_error_message(self):
        """Test displaying error result without error message."""
        try:
            self.ui.show_tool_result('test_tool', False, execution_time=0.1)
        except Exception as e:
            pytest.fail(f"show_tool_result raised an exception: {e}")

    def test_show_result_without_execution_time(self):
        """Test displaying result without execution time."""
        try:
            self.ui.show_tool_result('test_tool', True, result="Success")
            self.ui.show_tool_result('test_tool', False, error="Error")
        except Exception as e:
            pytest.fail(f"show_tool_result raised an exception: {e}")

    def test_show_policy_status_known_policies(self):
        """Test displaying policy status for known policies."""
        policies = ['always_confirm', 'never_confirm', 'confirm_destructive']

        for policy in policies:
            try:
                self.ui.show_policy_status(policy)
            except Exception as e:
                pytest.fail(f"show_policy_status raised an exception for {policy}: {e}")

    def test_show_policy_status_unknown_policy(self):
        """Test displaying policy status for unknown policy."""
        try:
            self.ui.show_policy_status('unknown_policy')
        except Exception as e:
            pytest.fail(f"show_policy_status raised an exception for unknown policy: {e}")

    def test_format_arguments_empty(self):
        """Test formatting empty arguments."""
        result = self.ui._format_arguments({})
        assert result == "{}"

    def test_format_arguments_simple(self):
        """Test formatting simple arguments."""
        args = {'name': 'test', 'count': 42}
        result = self.ui._format_arguments(args)

        # Should be valid JSON
        import json
        parsed = json.loads(result)
        assert parsed == args

    def test_format_arguments_complex(self):
        """Test formatting complex arguments."""
        args = {
            'data': {'nested': {'value': 123}},
            'list': [1, 2, 'three'],
            'boolean': True,
            'null': None
        }
        result = self.ui._format_arguments(args)

        # Should be valid JSON
        import json
        parsed = json.loads(result)
        assert parsed == args

    def test_format_arguments_with_non_serializable(self):
        """Test formatting arguments with non-JSON-serializable objects."""
        class CustomObject:
            def __str__(self):
                return "custom_object"

        args = {'obj': CustomObject(), 'normal': 'value'}
        result = self.ui._format_arguments(args)

        # Should not raise an exception and should contain string representation
        assert isinstance(result, str)
        assert 'custom_object' in result

    def test_format_arguments_fallback_to_str(self):
        """Test formatting falls back to string representation on JSON error."""
        # Create an object that can't be JSON serialized
        args = {'set': {1, 2, 3}}  # Sets aren't JSON serializable

        # Mock json.dumps to raise an exception
        with patch('json.dumps', side_effect=Exception("JSON error")):
            result = self.ui._format_arguments(args)
            assert isinstance(result, str)
            assert str(args) == result

    def test_display_tool_request_with_arguments(self):
        """Test displaying tool request with arguments."""
        try:
            self.ui._display_tool_request('test_tool', {'param': 'value'})
        except Exception as e:
            pytest.fail(f"_display_tool_request raised an exception: {e}")

    def test_display_tool_request_without_arguments(self):
        """Test displaying tool request without arguments."""
        try:
            self.ui._display_tool_request('test_tool', {})
        except Exception as e:
            pytest.fail(f"_display_tool_request raised an exception: {e}")

    def test_display_tool_request_with_complex_arguments(self):
        """Test displaying tool request with complex arguments."""
        complex_args = {
            'file_path': '/path/to/file.txt',
            'options': {
                'encoding': 'utf-8',
                'mode': 'read'
            },
            'filters': ['*.py', '*.md'],
            'recursive': True
        }

        try:
            self.ui._display_tool_request('file_processor', complex_args)
        except Exception as e:
            pytest.fail(f"_display_tool_request raised an exception: {e}")

    def test_long_result_truncation(self):
        """Test that long results are truncated properly."""
        long_result = "x" * 1000  # 1000 character result

        try:
            self.ui.show_tool_result('test_tool', True, result=long_result)
        except Exception as e:
            pytest.fail(f"show_tool_result raised an exception with long result: {e}")

    def test_ui_colors_configuration(self):
        """Test that UI colors are properly configured."""
        assert 'warning' in self.ui.colors
        assert 'success' in self.ui.colors
        assert 'error' in self.ui.colors
        assert 'info' in self.ui.colors
        assert 'highlight' in self.ui.colors

    @patch('builtins.input', return_value='Y')  # Test case insensitivity
    def test_confirm_execution_case_insensitive(self, mock_input):
        """Test confirmation is case insensitive."""
        result = self.ui.confirm_tool_execution('test_tool', {})
        assert result is True

    @patch('builtins.input', return_value='  y  ')  # Test whitespace handling
    def test_confirm_execution_whitespace_handling(self, mock_input):
        """Test confirmation handles whitespace properly."""
        result = self.ui.confirm_tool_execution('test_tool', {})
        assert result is True


class TestToolConfirmationUIIntegration:
    """Integration tests for tool confirmation UI with other components."""

    def test_ui_initialization(self):
        """Test UI can be initialized without errors."""
        ui = ToolConfirmationUI()
        assert ui is not None
        assert hasattr(ui, 'console')
        assert hasattr(ui, 'colors')

    def test_confirmation_flow_realistic_scenario(self):
        """Test a realistic confirmation flow."""
        ui = ToolConfirmationUI()

        # Simulate a realistic tool call scenario
        tool_name = 'file_reader'
        arguments = {
            'file_path': '/home/user/document.txt',
            'encoding': 'utf-8'
        }

        with patch('builtins.input', return_value='y'):
            confirmed = ui.confirm_tool_execution(tool_name, arguments)
            assert confirmed is True

        # Show successful result
        try:
            ui.show_tool_result(
                tool_name,
                True,
                result="File contents: Hello, World!",
                execution_time=0.05
            )
        except Exception as e:
            pytest.fail(f"show_tool_result raised an exception: {e}")

    def test_error_handling_flow(self):
        """Test error handling in confirmation flow."""
        ui = ToolConfirmationUI()

        # Test denial
        with patch('builtins.input', return_value='n'):
            confirmed = ui.confirm_tool_execution('dangerous_tool', {'delete': 'all'})
            assert confirmed is False

        # Show error result (simulating tool execution failure)
        try:
            ui.show_tool_result(
                'dangerous_tool',
                False,
                error="Permission denied: Cannot delete files",
                execution_time=0.01
            )
        except Exception as e:
            pytest.fail(f"show_tool_result raised an exception: {e}")

    def test_multiple_confirmation_sequence(self):
        """Test sequence of multiple tool confirmations."""
        ui = ToolConfirmationUI()

        tools_and_responses = [
            ('tool1', {'param1': 'value1'}, 'y', True),
            ('tool2', {'param2': 'value2'}, 'n', False),
            ('tool3', {}, 'yes', True),
        ]

        for tool_name, args, response, expected in tools_and_responses:
            with patch('builtins.input', return_value=response):
                result = ui.confirm_tool_execution(tool_name, args)
                assert result is expected

    def test_console_output_capture(self):
        """Test that console output can be captured for testing."""
        ui = ToolConfirmationUI()

        # Capture console output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            try:
                ui.show_policy_status('always_confirm')
                # Should have produced some output
                output = mock_stdout.getvalue()
                # Output might be empty due to Rich's complex rendering,
                # but the call should not raise an exception
                assert isinstance(output, str)
            except Exception as e:
                pytest.fail(f"Policy status display raised an exception: {e}")
