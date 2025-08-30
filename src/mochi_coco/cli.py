from typing import Optional
import typer

from .chat_controller import ChatController

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
    controller = ChatController(host=host)
    controller.run()


def main():
    app()


if __name__ == "__main__":
    main()
