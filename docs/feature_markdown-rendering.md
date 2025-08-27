---
project: mochi-coco
feature: markdown-rendering
---

# Markdown Rendering Feature

## Overview

Add optional markdown rendering support for LLM responses in the terminal using the Rich library. This feature provides beautiful formatting for code blocks, tables, headers, and other markdown elements while maintaining the streaming chat experience.

## User Experience

### Session Setup Flow
The user journey will be enhanced with markdown preference selection:

1. **Session Selection**: Choose existing session or 'new' 
2. **Model Selection**: Choose LLM model (if new session)
3. **Markdown Preference**: "Enable markdown rendering? (Y/n)" prompt
4. **Chat Start**: Begin conversation with chosen settings

### Chat Experience

#### With Markdown Enabled:
- **Phase 1**: Stream response as dim gray text (immediate feedback)
- **Phase 2**: Replace with beautifully formatted markdown when complete
- **Visual transition**: Smooth replacement using Rich Live context

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

## Technical Implementation

### Architecture Changes

#### New Dependencies
- `rich>=13.0.0` - Terminal markdown rendering and Live context

#### UI Module Enhancement  
- `ModelSelector.select_session_or_new()` returns markdown preference
- New prompt: "Enable markdown rendering?" with default=True
- Return signature: `tuple[ChatSession, str, bool]` (session, model, markdown_enabled)

#### CLI Module Enhancement
- Accept markdown preference parameter
- Pass preference to rendering logic
- Handle both markdown and plain text rendering paths

#### Rendering Implementation
```python
# Hybrid approach using Rich Live
def render_assistant_response(text_chunks, markdown_enabled):
    if markdown_enabled:
        with Live() as live:
            accumulated = ""
            # Phase 1: Stream as dim text
            for chunk in text_chunks:
                accumulated += chunk
                live.update(Text(accumulated, style="dim"))
            
            # Phase 2: Switch to formatted markdown
            live.update(Markdown(accumulated))
    else:
        # Current plain text streaming
        for chunk in text_chunks:
            print(chunk, end='', flush=True)
```

### Session Persistence
- **No session storage**: Markdown preference is per-session, not persisted
- **Rationale**: Visual preference, not conversation data
- **Future consideration**: Could be added to user config file

## Implementation Tasks

### Phase 1: Core Infrastructure
1. Add Rich dependency to `pyproject.toml`
2. Create markdown rendering utility functions
3. Update `OllamaClient` to support rendering callbacks

### Phase 2: UI Integration  
1. Enhance `ModelSelector` with markdown preference prompt
2. Update CLI flow to handle markdown preference
3. Implement hybrid rendering logic

### Phase 3: Testing & Polish
1. Test with various markdown content types
2. Verify terminal compatibility (Windows/macOS/Linux)
3. Handle edge cases (very long responses, terminal resizing)

## Error Handling

### Fallback Strategy
- If markdown rendering fails → gracefully fall back to plain text
- Log warning but don't break chat experience
- User sees response content regardless of formatting issues

### Terminal Compatibility
- Rich automatically detects terminal capabilities
- Degrades gracefully on terminals without color support
- Handles different terminal widths appropriately

## Future Enhancements

### Theme Customization
- Custom color schemes for different markdown elements
- Dark/light theme support
- User-configurable styling preferences

### Advanced Features
- Save markdown preference in user config
- Command-line flag: `mochi-coco --markdown` / `--no-markdown`
- Runtime toggle: `/markdown on/off` during chat

### Performance Optimizations
- Streaming markdown parser for very large responses
- Progressive rendering for better performance

## Testing Strategy

### Manual Testing
- Test all markdown elements (headers, code, tables, etc.)
- Verify streaming experience feels natural
- Test on different terminal sizes and types

### Edge Cases
- Very long code blocks
- Complex tables
- Mixed content (markdown + plain text)
- Terminal resizing during rendering

## Benefits

### For Users
- **Beautiful output**: Professional formatting for technical content
- **Better readability**: Code blocks with syntax highlighting
- **Flexible choice**: Can disable if preferred
- **Preserved streaming**: Maintains real-time chat feel

### For Developers  
- **Rich ecosystem**: Leverages mature, well-tested library
- **Minimal code**: Rich handles complexity automatically
- **Extensible**: Easy to add themes and customizations
- **Maintainable**: Clean separation of rendering logic

