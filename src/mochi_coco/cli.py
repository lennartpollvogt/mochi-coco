from typing import Optional

import typer
from .ollama import OllamaClient
from .ui import ModelSelector
from .chat import ChatSession

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
    model_selector = ModelSelector(client)

    # Session selection or new chat
    session, selected_model = model_selector.select_session_or_new()

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

    typer.secho("Type 'exit' to quit or '/models' to change model.\n", fg=typer.colors.BRIGHT_GREEN)

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

        if not user_input.strip():
            continue

        session.add_message("user", user_input)

        try:
            assistant_text = ""
            typer.secho("\nA:", fg=typer.colors.MAGENTA, bold=True)

            for text_chunk in client.chat_stream(selected_model, session.get_messages_for_api()):
                assistant_text += text_chunk
                print(text_chunk, end="", flush=True)

            print("\n")  # double newline after streaming finishes for spacing
            session.add_message("assistant", assistant_text)
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)



def main():
    app()


if __name__ == "__main__":
    main()
