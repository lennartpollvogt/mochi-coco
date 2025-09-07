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

def get_user_input(message: str = "") -> str:
    """
    Get user input with multiline support using prompt_toolkit.
    This is for chat messages where multiline input is desired.

    Args:
        message (str): The message to display as a prompt.
    """
    return get_user_input_multiline(message)


def get_user_input_single_line(message: str = "") -> str:
    """
    Get single-line user input using prompt_toolkit.
    This is for menu selections where only single-line input is needed.

    Args:
        message (str): The message to display as a prompt.
    """
    # Custom style for the prompt
    style = Style.from_dict({
        'prompt': '#00aa00 bold',
        'text': '#ffffff',
    })

    kb = create_key_bindings()

    try:
        user_input = prompt(
            message=message,
            multiline=False,  # Single line only - submit with Enter
            style=style,
            mouse_support=False,
            wrap_lines=True,
            key_bindings=kb,
        )
        return user_input.strip()
    except EOFError:
        return ""


def get_user_input_multiline(message: str = "") -> str:
    """
    Get user input with multiline support using prompt_toolkit.
    This is for chat messages where multiline input is desired.

    Args:
        message (str): The message to display as a prompt.
    """
    # Custom style for the prompt
    style = Style.from_dict({
        'prompt': '#00aa00 bold',
        'text': '#ffffff',
    })

    kb = create_key_bindings()

    try:
        user_input = prompt(
            message=message,
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


def get_user_input_with_prefill(message: str = "", prefill_text: str = "") -> str:
    """
    Get user input with multiline support and pre-filled content using prompt_toolkit.
    This is for editing existing chat messages.

    Args:
        message (str): The message to display as a prompt.
        prefill_text (str): Text to pre-fill the input field with.
    """
    # Custom style for the prompt
    style = Style.from_dict({
        'prompt': '#00aa00 bold',
        'text': '#ffffff',
    })

    kb = create_key_bindings()

    try:
        user_input = prompt(
            message=message,
            multiline=True,
            prompt_continuation="",  # Continuation prompt for multiline
            style=style,
            mouse_support=False,
            wrap_lines=True,
            # Submit with Enter when not in multiline mode, or Ctrl+Enter in multiline
            key_bindings=kb,  # Use default key bindings
            default=prefill_text,  # Pre-fill with existing content
        )
        return user_input.strip()
    except EOFError:
        return ""
