#!/usr/bin/env python3
"""Test script specifically for thinking block preprocessing."""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mochi_coco.rendering import MarkdownRenderer, RenderingMode


def test_thinking_block_preprocessing():
    """Test the _preprocess_thinking_blocks method directly."""

    renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN)

    print("Testing thinking block preprocessing (hide mode)...")
    print("=" * 50)

    # Test case 1: Simple <think> block (hiding)
    test1_input = "<think>\nOkay, the user said \"Hi\". I need to respond appropriately.\n</think>\n\nHello! How can I assist you today? 😊"
    test1_expected = "Hello! How can I assist you today? 😊"
    test1_result = renderer._preprocess_thinking_blocks(test1_input)

    print("\n1. Simple <think> block:")
    print(f"Input: {repr(test1_input)}")
    print(f"Expected: {repr(test1_expected)}")
    print(f"Got: {repr(test1_result)}")
    print(f"✅ PASS" if test1_result == test1_expected else "❌ FAIL")

    # Test case 2: <thinking> block
    test2_input = "<thinking>\nThis is a longer thinking process.\nMultiple lines here.\n</thinking>\n\nActual response here."
    test2_expected = "Actual response here."
    test2_result = renderer._preprocess_thinking_blocks(test2_input)

    print("\n2. <thinking> block:")
    print(f"Input: {repr(test2_input)}")
    print(f"Expected: {repr(test2_expected)}")
    print(f"Got: {repr(test2_result)}")
    print(f"✅ PASS" if test2_result == test2_expected else "❌ FAIL")

    # Test case 3: Multiple blocks
    test3_input = """<think>First thought</think>

First response.

<thinking>
Second thought here
with multiple lines
</thinking>

Second response with **markdown**."""
    test3_expected = """First response.

Second response with **markdown**."""
    test3_result = renderer._preprocess_thinking_blocks(test3_input)

    print("\n3. Multiple thinking blocks:")
    print(f"Input: {repr(test3_input)}")
    print(f"Expected: {repr(test3_expected)}")
    print(f"Got: {repr(test3_result)}")
    print(f"✅ PASS" if test3_result == test3_expected else "❌ FAIL")

    # Test case 4: Case insensitive
    test4_input = "<THINK>Upper case thinking</THINK>\n\nResponse here."
    test4_expected = "Response here."
    test4_result = renderer._preprocess_thinking_blocks(test4_input)

    print("\n4. Case insensitive:")
    print(f"Input: {repr(test4_input)}")
    print(f"Expected: {repr(test4_expected)}")
    print(f"Got: {repr(test4_result)}")
    print(f"✅ PASS" if test4_result == test4_expected else "❌ FAIL")

    # Test case 5: No thinking blocks (should be unchanged)
    test5_input = "Just a normal response with **markdown**."
    test5_expected = "Just a normal response with **markdown**."
    test5_result = renderer._preprocess_thinking_blocks(test5_input)

    print("\n5. No thinking blocks:")
    print(f"Input: {repr(test5_input)}")
    print(f"Expected: {repr(test5_expected)}")
    print(f"Got: {repr(test5_result)}")
    print(f"✅ PASS" if test5_result == test5_expected else "❌ FAIL")

    # Test with show_thinking=True
    print("\n" + "=" * 50)
    print("Testing thinking block preprocessing (show mode)...")
    print("=" * 50)

    renderer_show = MarkdownRenderer(mode=RenderingMode.MARKDOWN, show_thinking=True)

    # Test case 6: Simple <think> block (showing)
    test6_input = "<think>\nThis is my thinking process.\n</think>\n\nActual response."
    test6_expected = "> 💭 **Thinking:**\n>\n> This is my thinking process.\n\nActual response."
    test6_result = renderer_show._preprocess_thinking_blocks(test6_input)

    print("\n6. Simple <think> block (showing):")
    print(f"Input: {repr(test6_input)}")
    print(f"Expected: {repr(test6_expected)}")
    print(f"Got: {repr(test6_result)}")
    print(f"✅ PASS" if test6_result == test6_expected else "❌ FAIL")

    # Test case 7: <thinking> block (showing)
    test7_input = "<thinking>\nMultiple lines\nof thinking\n</thinking>\n\nResponse here."
    test7_expected = "> 💭 **Thinking:**\n>\n> Multiple lines\n> of thinking\n\nResponse here."
    test7_result = renderer_show._preprocess_thinking_blocks(test7_input)

    print("\n7. <thinking> block (showing):")
    print(f"Input: {repr(test7_input)}")
    print(f"Expected: {repr(test7_expected)}")
    print(f"Got: {repr(test7_result)}")
    print(f"✅ PASS" if test7_result == test7_expected else "❌ FAIL")



def test_full_rendering_with_thinking():
    """Test the full rendering process with thinking blocks hidden."""

    print("\n" + "=" * 50)
    print("Testing full rendering with thinking blocks HIDDEN")
    print("=" * 50)

    renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN, show_thinking=False)

    # Simulate the exact case from the user's example
    content = "<think>\nOkay, the user said \"Hi\". I need to respond appropriately. Let me check the guidelines. The response should be friendly and open-ended. Maybe ask how I can assist them. Keep it simple and welcoming. Avoid any technical jargon. Make sure to use proper grammar and punctuation. Alright, let's go with a friendly greeting and offer help.\n</think>\n\nHello! How can I assist you today? 😊"

    def stream_thinking_content():
        yield (content, None)
        yield ("", 100)

    print("\nRendering content with thinking block hidden...")
    print("-" * 30)

    text, context = renderer.render_streaming_response(stream_thinking_content())

    print("-" * 30)
    print("Above should only show: 'Hello! How can I assist you today? 😊'")
    print("(No thinking block content should be visible)")


def test_full_rendering_with_thinking_shown():
    """Test the full rendering process with thinking blocks shown."""

    print("\n" + "=" * 50)
    print("Testing full rendering with thinking blocks SHOWN")
    print("=" * 50)

    renderer = MarkdownRenderer(mode=RenderingMode.MARKDOWN, show_thinking=True)

    # Simulate content with thinking block
    content = "<think>\nThis is my thinking process.\nIt has multiple lines.\n</think>\n\nHere's the actual response with **markdown**."

    def stream_thinking_content():
        yield (content, None)
        yield ("", 100)

    print("\nRendering content with thinking block displayed as blockquote...")
    print("-" * 30)

    text, context = renderer.render_streaming_response(stream_thinking_content())

    print("-" * 30)
    print("Above should show thinking block as a formatted blockquote")
    print("followed by the actual response with markdown formatting")


if __name__ == "__main__":
    try:
        test_thinking_block_preprocessing()
        test_full_rendering_with_thinking()
        test_full_rendering_with_thinking_shown()
        print("\n🎉 All tests completed!")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
