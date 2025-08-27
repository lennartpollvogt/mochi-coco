#!/usr/bin/env python3
"""Integration test for chat history rendering with markdown support."""

import sys
from pathlib import Path
from unittest.mock import Mock

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mochi_coco.rendering import MarkdownRenderer, RenderingMode
from mochi_coco.chat import ChatSession
from mochi_coco.ui import ModelSelector
from mochi_coco.ollama.client import OllamaClient


def test_chat_history_integration():
    """Test that chat history displays correctly with markdown rendering."""

    print("\n" + "="*70)
    print("INTEGRATION TEST: CHAT HISTORY WITH MARKDOWN RENDERING")
    print("="*70)

    # Create a mock Ollama client
    mock_client = Mock(spec=OllamaClient)

    # Create test session with sample messages
    test_session = ChatSession(model="test-model")

    # Add some test messages with various content types
    test_session.add_message("user", "Hello, can you help me with Python?")

    assistant_response = """# Python Help

I'd be happy to help you with Python! Here are some basics:

## Data Types
- **Strings**: Text data
- **Integers**: Whole numbers
- **Lists**: Ordered collections

## Example Code
```python
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
```

What specific topic would you like to learn about?"""

    test_session.add_message("assistant", assistant_response)

    test_session.add_message("user", "Can you explain loops?")

    assistant_with_thinking = """<thinking>
The user wants to learn about loops. I should provide clear examples
of both for loops and while loops with practical examples.
</thinking>

# Python Loops

There are two main types of loops in Python:

## For Loops
```python
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit)
```

## While Loops
```python
count = 0
while count < 5:
    print(f"Count: {count}")
    count += 1
```

Both are useful for different scenarios!"""

    test_session.add_message("assistant", assistant_with_thinking)

    print("\n1. Testing with PLAIN rendering mode:")
    print("-" * 50)

    # Test with plain renderer
    plain_renderer = MarkdownRenderer(mode=RenderingMode.PLAIN)
    model_selector = ModelSelector(mock_client, plain_renderer)

    model_selector.display_chat_history(test_session)

    print("\n2. Testing with MARKDOWN rendering mode (thinking hidden):")
    print("-" * 50)

    # Test with markdown renderer, thinking blocks hidden
    markdown_renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN, show_thinking=False)
    model_selector_md = ModelSelector(mock_client, markdown_renderer)

    model_selector_md.display_chat_history(test_session)

    print("\n3. Testing with MARKDOWN rendering mode (thinking shown):")
    print("-" * 50)

    # Test with markdown renderer, thinking blocks shown
    markdown_renderer_thinking = MarkdownRenderer(mode=RenderingMode.MARKDOWN, show_thinking=True)
    model_selector_thinking = ModelSelector(mock_client, markdown_renderer_thinking)

    model_selector_thinking.display_chat_history(test_session)

    print("\n✅ Integration test complete!")
    print("\nExpected behavior:")
    print("1. Plain mode: Raw text without formatting")
    print("2. Markdown (thinking hidden): Formatted headers, code blocks, lists")
    print("3. Markdown (thinking shown): Same as #2 plus thinking blocks as quotes")


def test_empty_session_display():
    """Test that empty sessions are handled gracefully."""

    print("\n" + "="*70)
    print("INTEGRATION TEST: EMPTY SESSION DISPLAY")
    print("="*70)

    mock_client = Mock(spec=OllamaClient)
    empty_session = ChatSession(model="test-model")

    renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)
    model_selector = ModelSelector(mock_client, renderer)

    print("\nTesting empty session display:")
    print("-" * 30)

    model_selector.display_chat_history(empty_session)

    print("✅ Empty session test complete!")


def test_renderer_mode_switching():
    """Test that renderer mode switching works correctly during display."""

    print("\n" + "="*70)
    print("INTEGRATION TEST: RENDERER MODE SWITCHING")
    print("="*70)

    mock_client = Mock(spec=OllamaClient)
    test_session = ChatSession(model="test-model")

    # Add a message with markdown content
    markdown_message = """## Quick Reference

Here's a **simple** example:

```bash
pip install package-name
```

Hope this helps!"""

    test_session.add_message("assistant", markdown_message)

    # Create renderer and model selector
    renderer = MarkdownRenderer(mode=RenderingMode.PLAIN)
    model_selector = ModelSelector(mock_client, renderer)

    print("\n1. Initial display (PLAIN mode):")
    print("-" * 40)
    model_selector.display_chat_history(test_session)

    print("\n2. After switching to MARKDOWN mode:")
    print("-" * 40)
    renderer.set_mode(RenderingMode.MARKDOWN)
    model_selector.display_chat_history(test_session)

    print("\n3. After switching back to PLAIN mode:")
    print("-" * 40)
    renderer.set_mode(RenderingMode.PLAIN)
    model_selector.display_chat_history(test_session)

    print("\n✅ Mode switching test complete!")


def test_user_message_rendering():
    """Test that user messages are rendered with markdown during chat flow."""

    print("\n" + "="*70)
    print("INTEGRATION TEST: USER MESSAGE RENDERING")
    print("="*70)

    print("\n1. Testing user message in PLAIN mode:")
    print("-" * 40)

    plain_renderer = MarkdownRenderer(mode=RenderingMode.PLAIN)

    user_message_with_markdown = """# My Question

Can you help me with this **Python** code:

```python
def greet(name):
    return f"Hello, {name}!"
```

I want to understand how it works."""

    print("User message (should be plain text):")
    plain_renderer.render_static_text(user_message_with_markdown)

    print("\n2. Testing user message in MARKDOWN mode:")
    print("-" * 40)

    markdown_renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)

    print("User message (should be formatted):")
    markdown_renderer.render_static_text(user_message_with_markdown)

    print("\n3. Testing user message with thinking blocks (should be removed):")
    print("-" * 40)

    user_with_thinking = """<thinking>
Let me think about how to ask this question properly.
</thinking>

# My Real Question

How do I implement **error handling** in Python?

```python
try:
    result = risky_operation()
except Exception as e:
    print(f"Error: {e}")
```"""

    print("User message with thinking blocks:")
    markdown_renderer.render_static_text(user_with_thinking)

    print("\n✅ User message rendering test complete!")


def test_edge_cases():
    """Test edge cases in chat history rendering."""

    print("\n" + "="*70)
    print("INTEGRATION TEST: EDGE CASES")
    print("="*70)

    mock_client = Mock(spec=OllamaClient)
    renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)
    model_selector = ModelSelector(mock_client, renderer)

    # Test with very long message
    print("\n1. Testing very long message:")
    print("-" * 40)

    long_session = ChatSession(model="test-model")
    long_message = "This is a very long message. " * 50
    long_session.add_message("user", long_message)

    model_selector.display_chat_history(long_session)

    # Test with empty message content
    print("\n2. Testing empty message content:")
    print("-" * 40)

    empty_content_session = ChatSession(model="test-model")
    empty_content_session.add_message("user", "")
    empty_content_session.add_message("assistant", "")

    model_selector.display_chat_history(empty_content_session)

    # Test with malformed markdown
    print("\n3. Testing malformed markdown:")
    print("-" * 40)

    malformed_session = ChatSession(model="test-model")
    malformed_markdown = "# Unclosed header\n\n**Bold without closing\n\n```\ncode without closing"
    malformed_session.add_message("assistant", malformed_markdown)

    model_selector.display_chat_history(malformed_session)

    print("\n✅ Edge cases test complete!")


if __name__ == "__main__":
    try:
        test_chat_history_integration()
        test_empty_session_display()
        test_renderer_mode_switching()
        test_user_message_rendering()
        test_edge_cases()

        print("\n" + "="*70)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("="*70)

    except KeyboardInterrupt:
        print("\n\nTests interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
