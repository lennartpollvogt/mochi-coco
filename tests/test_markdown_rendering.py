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


if __name__ == "__main__":
    try:
        test_markdown_replacement()
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
