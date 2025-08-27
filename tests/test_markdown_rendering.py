#!/usr/bin/env python3
"""Simple test to verify markdown replacement works correctly."""

import sys
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mochi_coco.rendering import MarkdownRenderer, RenderingMode


def test_markdown_replacement():
    """Test that markdown replacement works correctly."""

    print("\n" + "="*60)
    print("TESTING MARKDOWN REPLACEMENT")
    print("="*60)
    print("\n1. Testing MARKDOWN mode (should replace plain with formatted):")
    print("-"*40)

    renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)

    # Create a generator that simulates streaming
    def stream_content():
        # Stream in chunks
        chunks = [
            ("# Test Header\n\n", None),
            ("This is **bold**", None),
            (" and *italic* text.\n\n", None),
            ("```python\n", None),
            ("print(\"Hello World!\")\n", None),
            ("```\n\n", None),
            ("- Item 1\n", None),
            ("- Item 2\n", None),
            ("", 100),  # Final chunk with context window
        ]

        for chunk in chunks:
            yield chunk
            time.sleep(0.05)  # Small delay to see streaming

    # Run the renderer
    text, context = renderer.render_streaming_response(stream_content())

    print("\n" + "-"*40)
    print(f"Complete! Context window: {context}")
    print("Above text should be formatted markdown (not plain text)")

    print("\n2. Testing PLAIN mode (should remain as plain text):")
    print("-"*40)

    renderer.set_mode(RenderingMode.PLAIN)

    def stream_simple():
        yield ("This is plain text mode.\n", None)
        yield ("No formatting applied.\n", None)
        yield ("", 50)

    text, context = renderer.render_streaming_response(stream_simple())

    print("-"*40)
    print(f"Complete! Context window: {context}")
    print("Above text should remain plain")

    print("\n✅ Test complete!")


def test_thinking_blocks():
    """Test that thinking blocks are properly handled during markdown rendering."""

    print("\n" + "="*60)
    print("TESTING THINKING BLOCK PREPROCESSING")
    print("="*60)

    renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)

    # Test case 1: Simple thinking block with <think> tags
    print("\n1. Testing <think> block removal:")
    print("-"*40)

    def stream_with_think():
        content = "<think>\nOkay, the user said \"Hi\". I need to respond appropriately. Let me check the guidelines.\n</think>\n\nHello! How can I assist you today? 😊"
        yield (content, None)
        yield ("", 100)

    text, context = renderer.render_streaming_response(stream_with_think())
    print("-"*40)
    print("Should only show: 'Hello! How can I assist you today? 😊'")

    # Test case 2: Thinking block with <thinking> tags
    print("\n2. Testing <thinking> block removal:")
    print("-"*40)

    def stream_with_thinking():
        content = "<thinking>\nThis is a longer thinking process.\nMultiple lines here.\n</thinking>\n\nActual response here."
        yield (content, None)
        yield ("", 100)

    text, context = renderer.render_streaming_response(stream_with_thinking())
    print("-"*40)
    print("Should only show: 'Actual response here.'")

    # Test case 3: Multiple thinking blocks
    print("\n3. Testing multiple thinking blocks:")
    print("-"*40)

    def stream_multiple_blocks():
        content = """<think>First thought</think>

First response.

<thinking>
Second thought here
with multiple lines
</thinking>

Second response with **markdown**."""
        yield (content, None)
        yield ("", 100)

    text, context = renderer.render_streaming_response(stream_multiple_blocks())
    print("-"*40)
    print("Should show both responses with markdown formatting")

    # Test case 4: Complex case with markdown in actual content
    print("\n4. Testing thinking block with markdown content:")
    print("-"*40)

    def stream_complex():
        content = """<think>
The user wants a code example.
I should provide Python code.
</think>

# Code Example

Here's a **Python** function:

```python
def greet(name):
    return f"Hello, {name}!"
```"""
        yield (content, None)
        yield ("", 100)

    text, context = renderer.render_streaming_response(stream_complex())
    print("-"*40)
    print("Should show formatted markdown with header, bold text, and code block")

    print("\n✅ Thinking block tests complete!")


if __name__ == "__main__":
    try:
        test_markdown_replacement()
        test_thinking_blocks()
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
