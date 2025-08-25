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

    typer.echo("Chat started. Type 'exit' to quit.")
    while True:
        try:
            user_input = typer.prompt("You")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nExiting.")
            break

        if user_input.strip().lower() in {"exit", "quit", ":q"}:
            typer.echo("Goodbye.")
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response_stream: Iterator = client.chat(
                model=model, messages=messages, stream=True
            )
            assistant_text = ""
            print("Assistant: ", end="", flush=True)

            for chunk in response_stream:
                if chunk.message and chunk.message.content:
                    text = chunk.message.content
                    assistant_text += text
                    print(text, end="", flush=True)

            print()  # newline after streaming finishes
            messages.append({"role": "assistant", "content": assistant_text})
        except Exception as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED)



def main():
    app()


if __name__ == "__main__":
    main()
