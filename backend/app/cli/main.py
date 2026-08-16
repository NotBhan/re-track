"""RE:Track (RefinedEngine Track) CLI entry point.

Typer application exposing backend API commands to developers.
All commands delegate to app.api.commands — no direct service calls.
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from app.api import commands as api
from app.api.schemas import (
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    IndexRepositoryRequest,
)

app = typer.Typer(
    name="retrack",
    help="RE:Track (RefinedEngine Track) — persistent memory for AI-assisted development.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


# --- Helpers ---


def _run(coro):
    """Run an async coroutine from sync Typer commands."""
    return asyncio.run(coro)


def _init_backend():
    """Initialize backend services with a spinner."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing backend...", total=None)
        _run(api.initialize_backend())
        progress.update(task, completed=True, description="[green]Backend ready")


def _handle_error(result) -> bool:
    """Display an ErrorResponse and return True if it was an error."""
    if isinstance(result, ErrorResponse):
        console.print(
            Panel(
                f"[red]{result.error}[/red]\n{result.message}",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
        return True
    return False


# --- Commands ---


@app.command("health")
def health_cmd():
    """Check system health: Ollama, Cognee, storage."""
    _init_backend()
    result = _run(api.health())

    if _handle_error(result):
        raise typer.Exit(1)

    status_color = "green" if result.status == "ok" else "yellow"
    table = Table(title="System Health", show_header=False, border_style="blue")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Status", f"[{status_color}]{result.status}[/{status_color}]")
    table.add_row("Ollama", "[green]reachable[/green]" if result.ollama_reachable else "[red]unreachable[/red]")
    table.add_row("Cognee", "[green]initialized[/green]" if result.cognee_initialized else "[red]not initialized[/red]")
    table.add_row("Version", result.version)
    console.print(table)


@app.command("status")
def status_cmd():
    """Show detailed backend status and configuration."""
    _init_backend()
    result = _run(api.get_backend_status())

    if _handle_error(result):
        raise typer.Exit(1)

    table = Table(title="Backend Status", border_style="blue")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_row("Status", result.status)
    table.add_row("Ollama Host", f"{result.ollama_host}:{result.ollama_port}")
    table.add_row("LLM Model", result.llm_model)
    table.add_row("Embedding Model", result.embedding_model)
    table.add_row("Vector DB", result.vector_db)
    table.add_row("Graph DB", result.graph_db)
    table.add_row("Relational DB", result.relational_db)
    table.add_row("Data Root", result.data_root)
    table.add_row("System Root", result.system_root)
    table.add_row("Cognee", "[green]initialized[/green]" if result.cognee_initialized else "[red]not initialized[/red]")
    console.print(table)


@app.command("index")
def index_cmd(
    repository: str = typer.Argument(..., help="Path to the repository to index"),
    dataset: str = typer.Option(..., "--dataset", "-d", help="Dataset name for memory namespace"),
    batch_size: int = typer.Option(10, "--batch-size", "-b", help="Files per ingestion batch"),
):
    """Index a repository into Cognee memory."""
    repo_path = Path(repository).resolve()
    if not repo_path.exists():
        console.print(f"[red]Repository path does not exist:[/red] {repository}")
        raise typer.Exit(1)
    if not repo_path.is_dir():
        console.print(f"[red]Path is not a directory:[/red] {repository}")
        raise typer.Exit(1)

    _init_backend()

    request = IndexRepositoryRequest(
        repository_path=str(repo_path),
        dataset_name=dataset,
        batch_size=batch_size,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Indexing {repo_path.name}...", total=None)
        result = _run(api.index_repository(request))
        progress.update(task, completed=True)

    if _handle_error(result):
        raise typer.Exit(1)

    status_color = "green" if result.success else "yellow"
    table = Table(title="Indexing Complete", border_style="blue")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Repository", result.repository_path)
    table.add_row("Dataset", result.dataset_name)
    table.add_row("Total Files", str(result.total_files))
    table.add_row("Processed", f"[green]{result.processed_files}[/green]")
    table.add_row("Failed", f"[red]{result.failed_files}[/red]" if result.failed_files else "0")
    table.add_row("Batches", str(result.total_batches))
    table.add_row("Status", f"[{status_color}]{'Success' if result.success else 'Partial'}[/{status_color}]")
    console.print(table)

    if result.failed_paths:
        console.print("\n[red]Failed files:[/red]")
        for p in result.failed_paths:
            console.print(f"  - {p}")


@app.command("context")
def context_cmd(
    query: str = typer.Option(..., "--query", "-q", help="Question or task description"),
    dataset: str = typer.Option(..., "--dataset", "-d", help="Dataset name to search"),
    top_k: int = typer.Option(15, "--top-k", "-k", help="Maximum memories to retrieve"),
):
    """Generate a Context Package for a developer task."""
    if not query.strip():
        console.print("[red]Query must not be empty[/red]")
        raise typer.Exit(1)

    _init_backend()

    request = GenerateContextRequest(
        task=query,
        datasets=[dataset],
        top_k=top_k,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating context...", total=None)
        result = _run(api.generate_context(request))
        progress.update(task, completed=True)

    if _handle_error(result):
        raise typer.Exit(1)

    console.print(
        Panel(
            f"Sources: [bold]{result.source_count}[/bold] | "
            f"Sections: [bold]{result.section_count}[/bold] | "
            f"~[bold]{result.token_estimate}[/bold] tokens",
            title="[bold green]Context Package[/bold green]",
            border_style="green",
        )
    )
    console.print()
    console.print(Markdown(result.markdown))


@app.command("forget")
def forget_cmd(
    dataset: Optional[str] = typer.Option(None, "--dataset", "-d", help="Dataset name to delete"),
    dataset_id: Optional[str] = typer.Option(None, "--dataset-id", help="UUID of dataset to delete"),
    data_id: Optional[str] = typer.Option(None, "--data-id", help="UUID of specific data item to delete"),
):
    """Forget (delete) a dataset from Cognee memory."""
    if not any([dataset, dataset_id, data_id]):
        console.print("[red]At least one of --dataset, --dataset-id, or --data-id must be provided[/red]")
        raise typer.Exit(1)

    _init_backend()

    request = ForgetDatasetRequest(
        dataset=dataset,
        dataset_id=dataset_id,
        data_id=data_id,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Forgetting dataset...", total=None)
        result = _run(api.forget_dataset(request))
        progress.update(task, completed=True)

    if _handle_error(result):
        raise typer.Exit(1)

    console.print("[green]Dataset forgotten successfully[/green]")


if __name__ == "__main__":
    app()
