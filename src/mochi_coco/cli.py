from typing import Iterator, List, Optional

import typer
from ollama import Client

app = typer.Typer()


@app.command()
def chat(
    model: str = typer.Option("gpt-oss:20b", "--model", "-m", help="Model to use"),
    host: Optional[str] = typer.Option(
        None, "--host", help="Ollama host (e.g. http://localhost:11434)"
    ),
):
    """
    Very simple CLI to chat with an LLM via Ollama using streaming responses.
    """
    client = Client(host=host) if host else Client()
    messages: List[dict] = []

    typer.secho("Chat started. Type 'exit' to quit.\n", fg=typer.colors.BRIGHT_GREEN)

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

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response_stream: Iterator = client.chat(
                model=model, messages=messages, stream=True
            )
            assistant_text = ""
            typer.secho("\nAssistant:", fg=typer.colors.MAGENTA, bold=True)

            for chunk in response_stream:
                if chunk.message and chunk.message.content:
                    text = chunk.message.content
                    assistant_text += text
                    print(text, end="", flush=True)

            print("\n")  # double newline after streaming finishes for spacing
            messages.append({"role": "assistant", "content": assistant_text})
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)



def main():
    app()


if __name__ == "__main__":
    main()
