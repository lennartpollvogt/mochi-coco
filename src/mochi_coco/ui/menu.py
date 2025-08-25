from typing import List, Optional
import typer
from ..ollama.client import OllamaClient, ModelInfo


class ModelSelector:
    def __init__(self, client: OllamaClient):
        self.client = client

    def display_models_table(self, models: List[ModelInfo]) -> None:
        """Display available models in a nice table format."""
        if not models:
            typer.secho("No models found!", fg=typer.colors.RED)
            return

        typer.secho("\nAvailable Models:", fg=typer.colors.BRIGHT_GREEN, bold=True)
        typer.echo("=" * 80)

        # Table header
        header = f"{'#':<3} {'Model Name':<30} {'Size (MB)':<12} {'Family':<15}"
        typer.secho(header, fg=typer.colors.CYAN, bold=True)
        typer.echo("-" * 80)

        # Table rows
        for i, model in enumerate(models, 1):
            size_str = f"{model.size_mb:.1f}" if model.size_mb else "N/A"
            family_str = model.family or "N/A"

            row = f"{i:<3} {model.name:<30} {size_str:<12} {family_str:<15}"
            typer.echo(row)

        typer.echo("=" * 80)

    def select_model(self) -> Optional[str]:
        """Display model selection menu and return the selected model name."""
        typer.secho("🤖 Model Selection", fg=typer.colors.BRIGHT_MAGENTA, bold=True)

        try:
            models = self.client.list_models()
        except Exception as e:
            typer.secho(f"Error loading models: {e}", fg=typer.colors.RED)
            return None

        if not models:
            typer.secho("No models available. Please install some models first.", fg=typer.colors.RED)
            return None

        self.display_models_table(models)

        while True:
            try:
                typer.secho(f"\nSelect a model (1-{len(models)}) or 'q' to quit:",
                           fg=typer.colors.YELLOW, bold=True)
                choice = input("Enter your choice: ").strip()

                if choice.lower() in {'q', 'quit', 'exit'}:
                    return None

                index = int(choice) - 1

                if 0 <= index < len(models):
                    selected_model = models[index].name
                    typer.secho(f"\n✅ Selected model: {selected_model}",
                               fg=typer.colors.GREEN, bold=True)
                    return selected_model
                else:
                    typer.secho(f"Please enter a number between 1 and {len(models)}",
                               fg=typer.colors.RED)

            except ValueError:
                typer.secho("Please enter a valid number", fg=typer.colors.RED)
            except (EOFError, KeyboardInterrupt):
                typer.secho("\nExiting model selection.", fg=typer.colors.YELLOW)
                return None
