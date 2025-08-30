from typing import Optional, Mapping, Any, List
import typer

from .ollama import OllamaClient
from .ui import ModelSelector
from .chat import ChatSession
from .rendering import MarkdownRenderer, RenderingMode
from .user_prompt import get_user_input

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

    typer.secho("Type 'exit' to quit, '/models' to change model, '/chats' to switch sessions, '/markdown' to toggle formatting, or '/thinking' to toggle thinking blocks.\n", fg=typer.colors.BRIGHT_GREEN)
    if markdown_enabled:
        typer.secho("Markdown rendering is enabled.", fg=typer.colors.CYAN)
        if show_thinking:
            typer.secho("Thinking blocks will be displayed.", fg=typer.colors.CYAN)

    def re_render_chat_history(session: ChatSession, model_selector) -> None:
        """Re-render the current chat history with current renderer settings."""
        # Add visual separation
        print("\n" + "=" * 80)
        print("REFRESHING CHAT HISTORY")
        print("=" * 80)

        # Re-display chat history with current renderer settings
        model_selector.display_chat_history(session)

    while True:
        try:
            typer.secho("You:", fg=typer.colors.CYAN, bold=True)
            user_input = get_user_input()
        except (EOFError, KeyboardInterrupt):
            typer.secho("\nExiting.", fg=typer.colors.YELLOW)
            break

        if user_input.strip().lower() in {"/exit", "/quit", "/q"}:
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

        # Handle chat session switching command
        if user_input.strip() == "/chats":
            typer.secho("\n🔄 Switching chat sessions...\n", fg=typer.colors.BLUE, bold=True)
            new_session, new_model, new_markdown_enabled, new_show_thinking = model_selector.select_session_or_new()

            if new_session is None and new_model is None:
                # User cancelled - continue with current session
                typer.secho("Returning to current session.\n", fg=typer.colors.YELLOW)
                continue

            # Update renderer settings with new preferences
            new_rendering_mode = RenderingMode.MARKDOWN if new_markdown_enabled else RenderingMode.PLAIN
            renderer.set_mode(new_rendering_mode)
            renderer.set_show_thinking(new_show_thinking)

            if new_session:
                # Switched to existing session
                session = new_session
                selected_model = session.metadata.model
                model_selector.display_chat_history(session)
                typer.secho(f"\n💬 Switched to session {session.session_id} with {selected_model}", fg=typer.colors.BRIGHT_GREEN)
            elif new_model:
                # Created new session with valid model
                session = ChatSession(model=new_model)
                selected_model = new_model
                typer.secho(f"\n💬 New chat started with {selected_model}", fg=typer.colors.BRIGHT_GREEN)
                typer.secho(f"Session ID: {session.session_id}", fg=typer.colors.CYAN)
            else:
                # This shouldn't happen, but handle gracefully
                typer.secho("Error: No session or model selected. Returning to current session.", fg=typer.colors.RED)
                continue

            # Show updated preferences
            if new_markdown_enabled:
                typer.secho("Markdown rendering is enabled.", fg=typer.colors.CYAN)
                if new_show_thinking:
                    typer.secho("Thinking blocks will be displayed.", fg=typer.colors.CYAN)

            continue

        # Handle markdown toggle command
        if user_input.strip() == "/markdown":
            # Toggle rendering mode
            current_mode = renderer.mode
            new_mode = RenderingMode.PLAIN if current_mode == RenderingMode.MARKDOWN else RenderingMode.MARKDOWN
            renderer.set_mode(new_mode)

            status = "enabled" if new_mode == RenderingMode.MARKDOWN else "disabled"
            typer.secho(f"\n✅ Markdown rendering {status}", fg=typer.colors.GREEN, bold=True)

            # Re-render chat history with new mode
            re_render_chat_history(session, model_selector)
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
                typer.secho(f"\n✅ Thinking blocks will be {status}", fg=typer.colors.GREEN, bold=True)

                # Re-render chat history with new thinking setting
                re_render_chat_history(session, model_selector)
            continue

        if not user_input.strip():
            continue

        # Add user message to session
        session.add_user_message(content=user_input)

        try:
            typer.secho("\nAssistant:", fg=typer.colors.MAGENTA, bold=True)

            # Use renderer for streaming response
            messages: List[Mapping[str, Any]] = session.get_messages_for_api()
            text_stream = client.chat_stream(selected_model, messages)
            final_chunk = renderer.render_streaming_response(text_stream)

            print()  # Extra newline for spacing
            if final_chunk:
                session.add_message(chunk=final_chunk)
            else:
                raise Exception("No response received. Final chunk: {final_chunk}")
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)


def main():
    app()


if __name__ == "__main__":
    main()
