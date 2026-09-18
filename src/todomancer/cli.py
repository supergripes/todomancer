from pathlib import Path

import typer
from rich.console import Console

from . import grouping, labeling, report, scanner

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def scan(
    path: str = typer.Argument(".", help="Directory to scan"),
    output: str = typer.Option(
        None, "--output", "-o", help="Also export the report to Markdown"
    ),
    threshold: float = typer.Option(
        grouping.DEFAULT_THRESHOLD,
        "--threshold",
        help="Cosine similarity threshold for grouping (0-1)",
    ),
):
    """Scan PATH for TODO/FIXME/HACK/XXX and produce a report."""
    root = Path(path).resolve()
    if not root.is_dir():
        console.print(f"[red]Error:[/red] '{path}' is not a valid directory.")
        raise typer.Exit(code=1)

    items = scanner.scan_directory(root)
    if not items:
        console.print("[green]No TODO/FIXME/HACK/XXX found.[/green]")
        return

    with console.status(f"Analyzing {len(items)} TODOs..."):
        groups = grouping.group_todos(items, threshold=threshold)
        summaries = labeling.summarize_groups(groups)

    report.render_report(summaries, root, console=console)

    if output:
        report.export_markdown(summaries, root, output)
        console.print(f"[dim]Report exported to {output}[/dim]")


if __name__ == "__main__":
    app()
