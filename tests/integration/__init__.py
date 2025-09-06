"""
Integration tests for the mochi-coco chat application.

This package contains integration tests that verify the interaction between
multiple components and test complete user workflows.

Test Categories:
- test_chat_flow.py: Complete chat workflows and end-to-end user journeys
- test_session_management.py: Session lifecycle and persistence integration
- test_command_processing.py: Command workflows and state management
- test_rendering_flow.py: Response rendering and markdown processing

These tests use real component instances where possible and mock only
external dependencies to ensure realistic behavior testing.
"""

import pytest

# Mark all tests in this package as integration tests
pytestmark = pytest.mark.integration
