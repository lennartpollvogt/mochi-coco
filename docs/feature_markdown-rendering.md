---
project: mochi-coco
feature: markdown-rendering
status: done
---

# Markdown Rendering Feature

## Overview

Add optional markdown rendering support for LLM responses in the terminal using the Rich library. This feature provides beautiful formatting for code blocks, tables, headers, and other markdown elements. The response streams as plain text first, then is replaced with formatted markdown after completion.

## User Experience

### Session Setup Flow
The user journey will be enhanced with markdown preference selection:

1. **Session Selection**: Choose existing session or 'new' 
2. **Model Selection**: Choose LLM model (if new session)
3. **Markdown Preference**: "Enable markdown rendering? (Y/n)" prompt
4. **Thinking Block Preference**: "Show thinking blocks? (y/N)" prompt (only if markdown enabled)
5. **Chat Start**: Begin conversation with chosen settings

### Chat Experience

#### With Markdown Enabled:
- **Streaming**: Response streams as plain text (exactly as current implementation)
- **Post-streaming**: After final chunk, replace entire response with formatted markdown
- **Clear benefit**: Users see immediate feedback, then get beautiful formatting

#### With Markdown Disabled:
- **Standard behavior**: Plain text streaming (current implementation)
- **No changes**: Existing chat experience preserved

### Markdown Elements Supported

Rich library automatically handles:
- **Headers**: `# ## ###` with different colors/sizes
- **Text Formatting**: `**bold**` and `*italic*` styling
- **Code Blocks**: ````python` with syntax highlighting
- **Inline Code**: `` `code` `` with background styling
- **Lists**: `- item` and `1. item` with proper indentation
- **Tables**: Proper borders and alignment
- **Links**: `[text](url)` highlighted and underlined
- **Blockquotes**: `> text` with special indentation
- **Horizontal Rules**: `---` with line styling
- **Thinking Blocks**: `<think>` or `<thinking>` tags handled specially (shown as blockquotes or hidden)

## Technical Implementation

### Architecture Changes

#### New Dependencies
- `rich>=13.0.0` - Terminal markdown rendering and Live context

#### UI Module Enhancement  
- `ModelSelector.select_session_or_new()` returns markdown and thinking preferences
- New prompts: 
  - "Enable markdown rendering?" with default=True
  - "Show thinking blocks?" with default=False (only if markdown enabled)
- Return signature: `tuple[ChatSession, str, bool, bool]` (session, model, markdown_enabled, show_thinking)

#### CLI Module Enhancement
- Accept markdown preference parameter
- Pass preference to rendering logic
- Handle both markdown and plain text rendering paths

#### Rendering Implementation
```python
# Rich Live context approach for seamless replacement
def render_streaming_response(text_chunks, markdown_enabled, show_thinking):
    if markdown_enabled:
        # Use Rich Live for seamless replacement
        with Live(console=console, refresh_per_second=60, auto_refresh=False) as live:
            accumulated = ""
            
            # Phase 1: Stream as plain text
            for chunk, context_window in text_chunks:
                if chunk:
                    accumulated += chunk
                    live.update(Text(accumulated))  # Show plain text
                    live.refresh()
            
            # Phase 2: Replace with markdown
            # Preprocess thinking blocks based on preference
            processed_text = preprocess_thinking_blocks(accumulated, show_thinking)
            live.update(Markdown(processed_text))  # Replace with formatted
            live.refresh()
    else:
        # Plain text mode (unchanged)
        for chunk, context_window in text_chunks:
            print(chunk, end='', flush=True)
```

### Session Persistence
- **No session storage**: Markdown preference is per-session, not persisted
- **Rationale**: Visual preference, not conversation data
- **Future consideration**: Could be added to user config file

## Implementation Tasks

### Phase 1: Core Infrastructure
1. Add Rich dependency to `pyproject.toml`
2. Create MarkdownRenderer class using Rich Live context
3. Implement rendering modes (PLAIN/MARKDOWN) with seamless replacement

### Phase 2: UI Integration  
1. Enhance `ModelSelector` with markdown preference prompt
2. Update CLI flow to handle markdown preference
3. Integrate MarkdownRenderer with streaming response handling

### Phase 3: Testing & Polish
1. Test with various markdown content types
2. Verify Rich Live replacement works correctly on different terminals
3. Handle edge cases (very long responses, rendering failures)

## Error Handling

### Fallback Strategy
- If markdown rendering fails → gracefully show plain text in Live context
- Display warning but don't break chat experience
- User sees response content regardless of formatting issues

### Terminal Compatibility
- Rich Live context handles all terminal complexity automatically
- Degrades gracefully on terminals without advanced features
- Cross-platform compatibility (Windows/macOS/Linux)

## Future Enhancements

### Theme Customization
- Custom color schemes for different markdown elements
- Dark/light theme support
- User-configurable styling preferences

### Advanced Features
- Save markdown preference in user config
- Command-line flag: `mochi-coco --markdown` / `--no-markdown`
- Runtime toggles: 
  - `/markdown` - Toggle markdown rendering
  - `/thinking` - Toggle thinking block display (markdown mode only)

### Performance Optimizations
- Rich Live context optimizes screen updates automatically
- Efficient refresh control for smooth transitions

## Testing Strategy

### Manual Testing
- Test all markdown elements (headers, code, tables, etc.)
- Verify Rich Live replacement works correctly on different terminals
- Test on different terminal sizes and types

### Edge Cases
- Very long code blocks
- Complex tables
- Mixed content (markdown + plain text)
- Rich Live rendering failures
- Thinking blocks with nested markdown content
- Multiple thinking blocks in one response

## Benefits

### For Users
- **Beautiful output**: Professional formatting for technical content
- **Better readability**: Code blocks with syntax highlighting
- **Flexible choice**: Can disable if preferred
- **Immediate feedback**: See response as it streams
- **Best of both worlds**: Real-time streaming + beautiful final output

### For Developers
- **Rich ecosystem**: Leverages mature, well-tested library
- **Minimal code**: Rich handles complexity automatically
- **Extensible**: Easy to add themes and customizations
- **Maintainable**: Clean separation of rendering logic
