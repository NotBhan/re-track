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

from app import __version__
from app.api import commands as api
from app.api.schemas import (
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    IndexRepositoryRequest,
)
from app.services.bootstrap_service import BootstrapService
from app.services.maintenance_service import MaintenanceService, ResetScope

def version_callback(value: bool):
    if value:
        console.print(f"RE:Track v{__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="retrack",
    help="RE:Track (RefinedEngine Track) — persistent memory for AI-assisted development.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the RE:Track version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """RE:Track (RefinedEngine Track) — persistent memory for AI-assisted development."""
    pass



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
    """Check system health: Ollama, Cognee, storage, cache, and concurrency."""
    _init_backend()
    result = _run(api.health())

    if _handle_error(result):
        raise typer.Exit(1)

    health_class = getattr(result, "health_state", "healthy" if result.status == "ok" else "degraded")
    if health_class == "healthy":
        status_color = "green"
    elif health_class == "degraded":
        status_color = "yellow"
    else:
        status_color = "red"

    table = Table(title="System Health & Operational Status", border_style="blue")
    table.add_column("Component", style="bold")
    table.add_column("Status / Metric")

    table.add_row("Overall Health", f"[{status_color}]{result.status} ({health_class})[/{status_color}]")
    table.add_row("Version", result.version)
    table.add_row("Ollama Provider", "[green]reachable[/green]" if result.ollama_reachable else "[yellow]unreachable (offline fallback active)[/yellow]")
    if result.active_model:
        table.add_row("Active Model", result.active_model)
    table.add_row("Memory Engine (Cognee)", "[green]initialized[/green]" if result.cognee_initialized else "[red]not initialized[/red]")
    table.add_row("Canonical Storage (~/.retrack/)", "[green]available[/green]" if getattr(result, "storage_canonical_writable", True) else "[red]unwritable[/red]")
    if getattr(result, "legacy_storage_detected", False):
        table.add_row("Legacy Storage (~/.andes/)", "[yellow]detected (run 'retrack migrate' to import)[/yellow]")
    table.add_row("Registered Repositories", str(getattr(result, "repository_count", 0)))
    table.add_row("Saved Context Packages", str(getattr(result, "context_package_count", 0)))
    table.add_row("Cached AST Files", f"{getattr(result, 'cache_files_count', 0)} files ({round(getattr(result, 'cache_total_bytes', 0) / 1024, 1)} KB)")
    table.add_row("Concurrency Queue Depth", f"{getattr(result, 'concurrency_queue_depth', 0)} / {getattr(result, 'concurrency_queue_capacity', 5)}")
    table.add_row("Host RAM Usage", f"{result.ram_used_gb:.1f} / {result.ram_total_gb:.1f} GB ({result.ram_percent:.1f}%)")
    table.add_row("Host CPU Usage", f"{result.cpu_percent:.1f}%")
    if result.gpu_name:
        table.add_row("GPU Device", result.gpu_name)
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


@app.command("diagnostics")
def diagnostics_cmd(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Target output filepath for JSON diagnostic bundle"),
    include_logs: bool = typer.Option(True, "--include-logs/--no-include-logs", help="Include recent structured log records"),
    include_config: bool = typer.Option(True, "--include-config/--no-include-config", help="Include sanitized configuration summary"),
    include_health: bool = typer.Option(True, "--include-health/--no-include-health", help="Include system health metrics"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw sanitized JSON to stdout"),
):
    """Generate and export sanitized operational diagnostic bundle."""
    from app.services.diagnostics_service import DiagnosticsService

    diag_service = DiagnosticsService()
    if json_output:
        report = diag_service.generate_diagnostics(
            include_logs=include_logs,
            include_config=include_config,
            include_health=include_health,
        )
        import json
        console.print(json.dumps(report, indent=2))
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Collecting operational diagnostics...", total=None)
        exported_path = diag_service.export_bundle(
            output_path=output,
            include_logs=include_logs,
            include_config=include_config,
            include_health=include_health,
        )
        progress.update(task, completed=True, description="[green]Diagnostics generated")

    console.print(
        Panel(
            f"[green]Diagnostic bundle successfully exported to:[/green]\n[bold]{exported_path}[/bold]\n\n"
            f"[dim]Privacy Guarantee: All credentials, source-code contents, and task prompts are strictly omitted or redacted.[/dim]",
            title="[bold green]RE:Track Diagnostics Export[/bold green]",
            border_style="green",
        )
    )


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


@app.command("init")
def init_cmd(
    check_provider: bool = typer.Option(
        True,
        "--check-provider/--no-check-provider",
        help="Check local LLM provider connectivity during initialization",
    ),
):
    """Initialize RE:Track environment, storage directories, and default settings."""
    service = BootstrapService()
    result = service.initialize(check_provider=check_provider)

    table = Table(title="RE:Track Initialization", border_style="blue")
    table.add_column("Property", style="bold")
    table.add_column("Status / Path")
    table.add_row("Version", result.version)
    table.add_row("Canonical Directory", result.retrack_dir)
    table.add_row("Created Directories", str(len(result.created_directories)))
    table.add_row("Existing Directories", str(len(result.existing_directories)))
    table.add_row("Created Files", str(len(result.created_files)))
    table.add_row("Preserved Files", str(len(result.preserved_files)))
    table.add_row(
        f"Provider ({result.provider_host}:{result.provider_port})",
        "[green]Reachable[/green]" if result.provider_reachable else "[yellow]Unreachable (Offline Fallback Active)[/yellow]",
    )
    if result.legacy_data_detected:
        table.add_row(
            "Legacy Storage",
            f"[cyan]Found {result.legacy_item_count} item(s) in {result.legacy_dir} (run 'retrack migrate')[/cyan]",
        )
    console.print(table)
    console.print(f"\n[green]{result.message}[/green]\n")


@app.command("reset")
def reset_cmd(
    cache: bool = typer.Option(
        False, "--cache", help="Clear only cached AST fingerprints and context chunks"
    ),
    state: bool = typer.Option(
        False, "--state", help="Reset registered repositories and packages (requires --confirm)"
    ),
    all_state: bool = typer.Option(
        False, "--all", help="Reset all ~/.retrack state to factory defaults (requires --confirm)"
    ),
    confirm: bool = typer.Option(
        False, "--confirm", "-y", help="Confirm destructive state reset operation"
    ),
):
    """Reset RE:Track cache or application state safely with automatic backup."""
    if not (cache or state or all_state):
        console.print("[red]Must specify one of --cache, --state, or --all[/red]")
        raise typer.Exit(1)

    service = MaintenanceService()

    if cache:
        result = service.reset_data(scope=ResetScope.CACHE, confirm=True)
        console.print(f"[green]{result.message}[/green]")
    elif state:
        if not confirm:
            console.print("[yellow]Warning: --state reset will clear registered repository metadata and packages.[/yellow]")
            confirm = typer.confirm("Are you sure you want to proceed with application state reset?")
            if not confirm:
                console.print("[dim]Operation aborted.[/dim]")
                raise typer.Exit(0)
        result = service.reset_data(scope=ResetScope.STATE, confirm=True)
        console.print(f"[green]{result.message}[/green]")
    elif all_state:
        if not confirm:
            console.print("[bold red]Warning: --all reset will reset all ~/.retrack configuration and data to defaults.[/bold red]")
            confirm = typer.confirm("Are you sure you want to proceed with full environment reset?")
            if not confirm:
                console.print("[dim]Operation aborted.[/dim]")
                raise typer.Exit(0)
        result = service.reset_data(scope=ResetScope.ALL, confirm=True)
        console.print(f"[green]{result.message}[/green]")


@app.command("migrate")
def migrate_cmd(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Preview items to migrate without copying"
    ),
):
    """Migrate legacy ~/.andes data into canonical ~/.retrack storage."""
    service = MaintenanceService()
    result = service.migrate_legacy_data(dry_run=dry_run)

    if result.dry_run:
        console.print(Panel(result.message, title="[cyan]Migration Dry Run[/cyan]", border_style="cyan"))
        if result.items_migrated:
            table = Table(title="Items to Migrate", border_style="cyan")
            table.add_column("Type", style="bold")
            table.add_column("Source")
            table.add_column("Target")
            table.add_column("Size (Bytes)")
            for item in result.items_migrated:
                table.add_row(item.item_type, item.source_path, item.target_path, str(item.size_bytes))
            console.print(table)
    else:
        if result.items_migrated:
            console.print(Panel(result.message, title="[green]Migration Complete[/green]", border_style="green"))
        else:
            console.print(f"[yellow]{result.message}[/yellow]")


@app.command("mcp")
def mcp_cmd():
    """Start the RE:Track Model Context Protocol (MCP) server over stdio."""
    from app.mcp.server import run_mcp_stdio
    _run(run_mcp_stdio())


if __name__ == "__main__":
    app()

