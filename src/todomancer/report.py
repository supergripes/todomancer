"""Terminal report (rich) and Markdown export."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.text import Text

from .labeling import GroupSummary

HIGH_THRESHOLD = 3.0
MEDIUM_THRESHOLD = 2.0


def priority_level(score: float) -> tuple[str, str]:
    """Returns (label, rich color) for a group's score.

    Fixed thresholds (not percentiles): stay stable regardless of how many
    groups a scan produces.
    """
    if score >= HIGH_THRESHOLD:
        return "high", "red"
    if score >= MEDIUM_THRESHOLD:
        return "medium", "yellow"
    return "low", "green"


def _file_link(root: Path, item) -> Text:
    abs_path = (root / item.file).resolve()
    location = f"{item.file}:{item.line}"
    return Text(location, style=f"link file://{abs_path}#{item.line}")


def render_report(
    summaries: list[GroupSummary],
    root: Path,
    console: Console | None = None,
) -> None:
    console = console or Console()
    if not summaries:
        console.print("[green]No TODO/FIXME/HACK/XXX found.[/green]")
        return

    for summary in summaries:
        level, color = priority_level(summary.score)
        count = len(summary.group.items)
        console.print(
            f"[bold {color}]● {summary.label}[/bold {color}]"
            f"  ({level} priority, score {summary.score:.2f},"
            f" {count} item{'' if count == 1 else 's'})"
        )
        for item in summary.group.items:
            line = Text("  ")
            line.append(f"[{item.marker}] ", style=f"bold {color}")
            line.append(_file_link(root, item))
            line.append(f"  {item.text}")
            console.print(line)
        console.print()


def export_markdown(
    summaries: list[GroupSummary],
    root: Path,
    output_path: str | Path,
) -> None:
    lines = ["# todomancer report", ""]
    if not summaries:
        lines.append("No TODO/FIXME/HACK/XXX found.")
    for summary in summaries:
        level, _ = priority_level(summary.score)
        lines.append(
            f"## {summary.label}: {level} priority (score {summary.score:.2f})"
        )
        lines.append("")
        for item in summary.group.items:
            lines.append(f"- `{item.file}:{item.line}` **[{item.marker}]** {item.text}")
        lines.append("")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
