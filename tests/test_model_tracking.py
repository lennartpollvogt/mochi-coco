#!/usr/bin/env python3
"""Test for model tracking in chat messages."""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mochi_coco.chat import ChatSession
from mochi_coco.rendering import MarkdownRenderer, RenderingMode
from mochi_coco.ui import ModelSelector
from mochi_coco.ollama.client import OllamaClient


def test_message_model_tracking():
    """Test that messages properly track which model created them."""

    print("\n" + "="*60)
    print("TESTING MESSAGE MODEL TRACKING")
    print("="*60)

    # Create a temporary directory for test sessions
    with tempfile.TemporaryDirectory() as temp_dir:
        session = ChatSession(model="llama2", sessions_dir=temp_dir)

        print("\n1. Testing initial model assignment:")
        print("-"*40)

        # Add a message - user should have no model, assistant should use session model
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        assert session.messages[0].model is None  # User messages don't track model
        assert session.messages[1].model == "llama2"
        print(f"✅ User message model: {session.messages[0].model}")
        print(f"✅ Assistant message model: {session.messages[1].model}")

        print("\n2. Testing explicit model assignment:")
        print("-"*40)

        # Add messages with explicit model names - user model should still be None
        session.add_message("user", "What can you do?", model="llama2")
        session.add_message("assistant", "I can help with various tasks.", model="llama2")

        assert session.messages[2].model is None  # User messages ignore model parameter
        assert session.messages[3].model == "llama2"
        print(f"✅ Explicit user model: {session.messages[2].model}")
        print(f"✅ Explicit assistant model: {session.messages[3].model}")

        print("\n3. Testing model change during session:")
        print("-"*40)

        # Simulate model change
        session.model = "codellama"
        session.add_message("user", "Can you code?", model="codellama")
        session.add_message("assistant", "Yes, I can write code!", model="codellama")

        assert session.messages[4].model is None  # User messages never track model
        assert session.messages[5].model == "codellama"
        print(f"✅ New user model after change: {session.messages[4].model}")
        print(f"✅ New assistant model after change: {session.messages[5].model}")

        print("\n4. Testing session persistence with model info:")
        print("-"*40)

        # Save and reload session
        session.save_session()

        # Create new session instance and load
        new_session = ChatSession(model="temp", session_id=session.session_id, sessions_dir=temp_dir)
        assert new_session.load_session()

        # Verify all model information is preserved
        assert len(new_session.messages) == 6
        assert new_session.messages[0].model is None  # User message
        assert new_session.messages[1].model == "llama2"  # Assistant message
        assert new_session.messages[4].model is None  # User message
        assert new_session.messages[5].model == "codellama"  # Assistant message

        print(f"✅ Session reloaded with {len(new_session.messages)} messages")
        print(f"✅ First user message model: {new_session.messages[0].model}")
        print(f"✅ Last assistant message model: {new_session.messages[5].model}")


def test_chat_history_model_display():
    """Test that chat history shows model information when multiple models are used."""

    print("\n" + "="*60)
    print("TESTING CHAT HISTORY MODEL DISPLAY")
    print("="*60)

    # Create mock client and renderer
    mock_client = Mock(spec=OllamaClient)
    renderer = MarkdownRenderer(mode=RenderingMode.PLAIN)
    model_selector = ModelSelector(mock_client, renderer)

    with tempfile.TemporaryDirectory() as temp_dir:
        print("\n1. Testing single model session (no model labels):")
        print("-"*40)

        single_model_session = ChatSession(model="llama2", sessions_dir=temp_dir)
        single_model_session.add_message("user", "Hello")
        single_model_session.add_message("assistant", "Hi there!", model="llama2")

        print("Single model session history:")
        model_selector.display_chat_history(single_model_session)

        print("\n2. Testing multi-model session (with model labels):")
        print("-"*40)

        multi_model_session = ChatSession(model="llama2", sessions_dir=temp_dir)
        multi_model_session.add_message("user", "Hello")
        multi_model_session.add_message("assistant", "Hi! I'm llama2.", model="llama2")
        multi_model_session.add_message("user", "Can you code?")
        multi_model_session.add_message("assistant", "Yes! I'm codellama, specialized in coding.", model="codellama")
        multi_model_session.add_message("user", "What about general questions?")
        multi_model_session.add_message("assistant", "I'm mixtral, good for general tasks!", model="mixtral")

        print("Multi-model session history:")
        model_selector.display_chat_history(multi_model_session)


def test_backward_compatibility():
    """Test backward compatibility with messages that don't have model field."""

    print("\n" + "="*60)
    print("TESTING BACKWARD COMPATIBILITY")
    print("="*60)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a session file manually without model field in messages
        session_id = "test123456"
        session_file = Path(temp_dir) / f"{session_id}.json"

        legacy_data = {
            "metadata": {
                "session_id": session_id,
                "model": "llama2",
                "created_at": "2023-01-01T12:00:00",
                "updated_at": "2023-01-01T12:05:00",
                "message_count": 2
            },
            "messages": [
                {
                    "role": "user",
                    "content": "Hello from legacy format",
                    "timestamp": "2023-01-01T12:00:00"
                    # Note: no model field
                },
                {
                    "role": "assistant",
                    "content": "Hi! This is a legacy message too.",
                    "timestamp": "2023-01-01T12:01:00"
                    # Note: no model field
                }
            ]
        }

        with open(session_file, 'w') as f:
            json.dump(legacy_data, f)

        print("\n1. Loading legacy session format:")
        print("-"*40)

        # Load the legacy session
        session = ChatSession(model="current", session_id=session_id, sessions_dir=temp_dir)
        loaded = session.load_session()

        assert loaded, "Failed to load legacy session"
        assert len(session.messages) == 2

        # Legacy messages should have model=None
        assert session.messages[0].model is None
        assert session.messages[1].model is None

        print(f"✅ Loaded {len(session.messages)} legacy messages")
        print(f"✅ Message 1 model: {session.messages[0].model}")
        print(f"✅ Message 2 model: {session.messages[1].model}")

        print("\n2. Adding new messages to legacy session:")
        print("-"*40)

        # Add new messages with model info
        session.add_message("user", "This is a new message")
        session.add_message("assistant", "New response with model tracking", model="llama3")

        assert session.messages[2].model is None  # User message
        assert session.messages[3].model == "llama3"  # Assistant message

        print("✅ New message models properly tracked")
        print(f"✅ Message 3 (user) model: {session.messages[2].model}")
        print(f"✅ Message 4 (assistant) model: {session.messages[3].model}")

        print("\n3. Testing mixed legacy/new session display:")
        print("-"*40)

        mock_client = Mock(spec=OllamaClient)
        renderer = MarkdownRenderer(mode=RenderingMode.PLAIN)
        model_selector = ModelSelector(mock_client, renderer)

        print("Mixed session history (legacy + new with models):")
        model_selector.display_chat_history(session)


def test_model_info_edge_cases():
    """Test edge cases for model information display."""

    print("\n" + "="*60)
    print("TESTING MODEL INFO EDGE CASES")
    print("="*60)

    mock_client = Mock(spec=OllamaClient)
    renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)
    model_selector = ModelSelector(mock_client, renderer)

    with tempfile.TemporaryDirectory() as temp_dir:
        print("\n1. Testing session with None model values:")
        print("-"*40)

        none_model_session = ChatSession(model="current", sessions_dir=temp_dir)
        none_model_session.add_message("user", "Test message")
        none_model_session.add_message("assistant", "Response", model=None)

        print("Session with None model values:")
        model_selector.display_chat_history(none_model_session)

        print("\n2. Testing empty session:")
        print("-"*40)

        empty_session = ChatSession(model="test", sessions_dir=temp_dir)

        print("Empty session:")
        model_selector.display_chat_history(empty_session)

        print("\n3. Testing session with model different from metadata:")
        print("-"*40)

        mismatch_session = ChatSession(model="current_model", sessions_dir=temp_dir)
        mismatch_session.add_message("user", "Old message")
        mismatch_session.add_message("assistant", "Old response", model="old_model")

        print("Session with model mismatch:")
        model_selector.display_chat_history(mismatch_session)


if __name__ == "__main__":
    try:
        test_message_model_tracking()
        test_chat_history_model_display()
        test_backward_compatibility()
        test_model_info_edge_cases()

        print("\n" + "="*60)
        print("🎉 ALL MODEL TRACKING TESTS PASSED!")
        print("="*60)

    except KeyboardInterrupt:
        print("\n\nTests interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
