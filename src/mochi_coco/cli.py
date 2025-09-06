from typing import Optional
import typer
import asyncio


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
    async def run_with_background_tasks():
        """Run the chat controller with support for background async tasks."""
        # Get the current event loop
        loop = asyncio.get_event_loop()

        # Create controller with the event loop
        controller = ChatController(host=host, event_loop=loop)

        # Run the synchronous chat in a separate thread to allow async background tasks
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit the sync chat controller to run in a thread
            chat_future = executor.submit(controller.run)

            # Wait for the chat to complete
            try:
                await asyncio.wrap_future(chat_future)
            except KeyboardInterrupt:
                pass

    # Run the async wrapper
    try:
        asyncio.run(run_with_background_tasks())
    except KeyboardInterrupt:
        typer.secho("\nGoodbye!", fg=typer.colors.YELLOW)


def main():
    app()


if __name__ == "__main__":
    main()
