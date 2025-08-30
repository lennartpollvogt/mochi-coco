from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

def create_key_bindings():
    """Create custom key bindings for the input."""
    kb = KeyBindings()

    @kb.add('c-c')  # Ctrl+C
    def _(event):
        """Handle Ctrl+C - exit gracefully."""
        event.app.exit(exception=KeyboardInterrupt)

    return kb

def get_user_input() -> str:
    """Get user input with multiline support using prompt_toolkit."""

    # Custom style for the prompt
    style = Style.from_dict({
        'prompt': '#00aa00 bold',
        'text': '#ffffff',
    })

    kb = create_key_bindings()

    try:
        user_input = prompt(
            message="",
            multiline=True,
            prompt_continuation="",  # Continuation prompt for multiline
            style=style,
            mouse_support=False,
            wrap_lines=True,
            # Submit with Enter when not in multiline mode, or Ctrl+Enter in multiline
            key_bindings=kb,  # Use default key bindings
        )
        return user_input.strip()
    except EOFError:
        return ""
