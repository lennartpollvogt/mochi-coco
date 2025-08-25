from typing import List, Optional

import typer
from .ollama import OllamaClient
from .ui import ModelSelector

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

    # Model selection menu
    model_selector = ModelSelector(client)
    selected_model = model_selector.select_model()

    if not selected_model:
        typer.secho("No model selected. Exiting.", fg=typer.colors.YELLOW)
        return

    # Start chat
    messages: List[dict] = []
    typer.secho(f"\n💬 Chat started with {selected_model}. Type '/exit' or '/quit' to quit.\n",
                fg=typer.colors.BRIGHT_GREEN)

    while True:
        try:
            typer.secho("You:", fg=typer.colors.CYAN, bold=True)
            user_input = input()
        except (EOFError, KeyboardInterrupt):
            typer.secho("\nExiting.", fg=typer.colors.YELLOW)
            break

        if user_input.strip().lower() in {"/exit", "/quit", ":q"}:
            typer.secho("Goodbye.", fg=typer.colors.YELLOW)
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            assistant_text = ""
            typer.secho("\nAssistant:", fg=typer.colors.MAGENTA, bold=True)

            for text_chunk in client.chat_stream(selected_model, messages):
                assistant_text += text_chunk
                print(text_chunk, end="", flush=True)

            print("\n")  # double newline after streaming finishes for spacing
            messages.append({"role": "assistant", "content": assistant_text})
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)



def main():
    app()


if __name__ == "__main__":
    main()
