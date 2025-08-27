---
project: mochi-coco
feature: markdown-rendering
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
4. **Chat Start**: Begin conversation with chosen settings

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
# Simple post-streaming markdown replacement
def render_assistant_response(text_chunks, markdown_enabled):
    accumulated = ""
    
    # Always stream as plain text first
    for chunk in text_chunks:
        accumulated += chunk
        print(chunk, end='', flush=True)
    
    # After streaming complete, optionally replace with markdown
    if markdown_enabled:
        # Clear the plain text output
        lines_printed = accumulated.count('\n') + 1
        for _ in range(lines_printed):
            sys.stdout.write('\033[1A\033[2K')  # Move up and clear line
        
        # Print formatted markdown
        console.print(Markdown(accumulated))
```

### Session Persistence
- **No session storage**: Markdown preference is per-session, not persisted
- **Rationale**: Visual preference, not conversation data
- **Future consideration**: Could be added to user config file

## Implementation Tasks

### Phase 1: Core Infrastructure
1. Add Rich dependency to `pyproject.toml`
2. Create utility functions for clearing terminal lines
3. Create markdown rendering function using Rich

### Phase 2: UI Integration  
1. Enhance `ModelSelector` with markdown preference prompt
2. Update CLI flow to handle markdown preference
3. Implement post-streaming replacement logic

### Phase 3: Testing & Polish
1. Test with various markdown content types
2. Verify line clearing works correctly on different terminals
3. Handle edge cases (very long responses, wrapped lines)

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
- Efficient line counting for accurate clearing
- Optimized rendering for very large responses

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
- **Immediate feedback**: See response as it streams
- **Best of both worlds**: Real-time streaming + beautiful final output

### For Developers  
- **Rich ecosystem**: Leverages mature, well-tested library
- **Minimal code**: Rich handles complexity automatically
- **Extensible**: Easy to add themes and customizations
- **Maintainable**: Clean separation of rendering logic

