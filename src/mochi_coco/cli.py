from typing import Optional

import typer
from .ollama import OllamaClient
from .ui import ModelSelector
from .chat import ChatSession
from .rendering import MarkdownRenderer, RenderingMode

app = typer.Typer()


@app.command()
def chat(
    host: Optional[str] = typer.Option(
        None, "--host", help="Ollama host (e.g. http://localhost:11434)"
    ),
):
    """
    Chat with an LLM via Ollama using streaming responses.
    """
    # Initialize Ollama client
    client = OllamaClient(host=host)

    # Initialize renderer with default settings (will be updated based on user preferences)
    renderer = MarkdownRenderer(mode=RenderingMode.PLAIN, show_thinking=False)
    model_selector = ModelSelector(client, renderer)

    # Session selection or new chat
    session, selected_model, markdown_enabled, show_thinking = model_selector.select_session_or_new()

    # Update renderer settings based on user preferences
    rendering_mode = RenderingMode.MARKDOWN if markdown_enabled else RenderingMode.PLAIN
    renderer.set_mode(rendering_mode)
    renderer.set_show_thinking(show_thinking)

    if session is None and selected_model is None:
        typer.secho("Exiting.", fg=typer.colors.YELLOW)
        return

    # Handle new session
    if session is None:
        if not selected_model:
            typer.secho("No model selected. Exiting.", fg=typer.colors.YELLOW)
            return
        session = ChatSession(model=selected_model)
        typer.secho(f"\n💬 New chat started with {selected_model}",
                    fg=typer.colors.BRIGHT_GREEN)
        typer.secho(f"Session ID: {session.session_id}", fg=typer.colors.CYAN)
    else:
        # Handle existing session
        model_selector.display_chat_history(session)
        selected_model = session.metadata.model
        typer.secho(f"\n💬 Continuing chat with {selected_model}",
                    fg=typer.colors.BRIGHT_GREEN)

    typer.secho("Type 'exit' to quit, '/models' to change model, '/markdown' to toggle formatting, or '/thinking' to toggle thinking blocks.\n", fg=typer.colors.BRIGHT_GREEN)
    if markdown_enabled:
        typer.secho("Markdown rendering is enabled.", fg=typer.colors.CYAN)
        if show_thinking:
            typer.secho("Thinking blocks will be displayed.", fg=typer.colors.CYAN)

    while True:
        try:
            typer.secho("You:", fg=typer.colors.CYAN, bold=True)
            user_input = input()
        except (EOFError, KeyboardInterrupt):
            typer.secho("\nExiting.", fg=typer.colors.YELLOW)
            break

        if user_input.strip().lower() in {"exit", "quit", ":q"}:
            typer.secho("Goodbye.", fg=typer.colors.YELLOW)
            break

        # Handle model change command
        if user_input.strip() == "/models":
            new_model = model_selector.select_model()
            if new_model:
                selected_model = new_model
                session.model = new_model
                session.metadata.model = new_model
                session.save_session()
                typer.secho(f"\n✅ Switched to model: {new_model}\n", fg=typer.colors.GREEN, bold=True)
            continue

        # Handle markdown toggle command
        if user_input.strip() == "/markdown":
            # Toggle rendering mode
            current_mode = renderer.mode
            new_mode = RenderingMode.PLAIN if current_mode == RenderingMode.MARKDOWN else RenderingMode.MARKDOWN
            renderer.set_mode(new_mode)

            status = "enabled" if new_mode == RenderingMode.MARKDOWN else "disabled"
            typer.secho(f"\n✅ Markdown rendering {status}\n", fg=typer.colors.GREEN, bold=True)
            continue

        # Handle thinking toggle command
        if user_input.strip() == "/thinking":
            if renderer.mode == RenderingMode.PLAIN:
                typer.secho("\n⚠️ Thinking blocks can only be toggled in markdown mode.", fg=typer.colors.YELLOW)
                typer.secho("Enable markdown first with '/markdown' command.\n", fg=typer.colors.YELLOW)
            else:
                # Toggle thinking blocks
                current_show = renderer.show_thinking
                renderer.set_show_thinking(not current_show)
                status = "shown" if not current_show else "hidden"
                typer.secho(f"\n✅ Thinking blocks will be {status}\n", fg=typer.colors.GREEN, bold=True)
            continue

        if not user_input.strip():
            continue

        # Display user message with markdown rendering
        typer.secho("\nYou:", fg=typer.colors.CYAN, bold=True)
        renderer.render_static_text(user_input)

        session.add_message("user", user_input)

        try:
            typer.secho("\nA:", fg=typer.colors.MAGENTA, bold=True)

            # Use renderer for streaming response
            text_stream = client.chat_stream(selected_model, session.get_messages_for_api())
            assistant_text, context_window = renderer.render_streaming_response(text_stream)

            print()  # Extra newline for spacing
            session.add_message("assistant", assistant_text, context_window)
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)



def main():
    app()


if __name__ == "__main__":
    main()
