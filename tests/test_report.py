import io
from pathlib import Path

from rich.console import Console

from todomancer.grouping import Group
from todomancer.labeling import GroupSummary
from todomancer.report import export_markdown, priority_level, render_report
from todomancer.scanner import TodoItem


def make_summary(label: str, score: float, marker: str = "TODO", text: str = "do it") -> GroupSummary:
    item = TodoItem(file=Path("f.py"), line=3, marker=marker, text=text, context=text, mtime=0.0)
    return GroupSummary(group=Group(items=[item]), label=label, score=score)


def test_priority_level_high():
    assert priority_level(3.0) == ("high", "red")
    assert priority_level(5.0) == ("high", "red")


def test_priority_level_medium():
    assert priority_level(2.0) == ("medium", "yellow")
    assert priority_level(2.99) == ("medium", "yellow")


def test_priority_level_low():
    assert priority_level(1.99) == ("low", "green")
    assert priority_level(0.0) == ("low", "green")


def test_render_report_empty_summaries(tmp_path):
    buffer = io.StringIO()
    console = Console(file=buffer, width=120)

    render_report([], tmp_path, console=console)

    assert "No TODO/FIXME/HACK/XXX found." in buffer.getvalue()


def test_render_report_includes_label_marker_and_location(tmp_path):
    buffer = io.StringIO()
    console = Console(file=buffer, width=120)
    summary = make_summary("parser / refactor", score=3.5, marker="FIXME", text="fix the parser")

    render_report([summary], tmp_path, console=console)

    output = buffer.getvalue()
    assert "parser / refactor" in output
    assert "FIXME" in output
    assert "high priority" in output
    assert "f.py:3" in output
    assert "fix the parser" in output


def test_export_markdown_empty_summaries(tmp_path):
    output_path = tmp_path / "report.md"

    export_markdown([], tmp_path, output_path)

    content = output_path.read_text()
    assert "No TODO/FIXME/HACK/XXX found." in content


def test_export_markdown_writes_group_and_items(tmp_path):
    output_path = tmp_path / "report.md"
    summary = make_summary("parser / refactor", score=2.0, marker="TODO", text="fix the parser")

    export_markdown([summary], tmp_path, output_path)

    content = output_path.read_text()
    assert "parser / refactor" in content
    assert "medium priority" in content
    assert "`f.py:3`" in content
    assert "**[TODO]**" in content
    assert "fix the parser" in content
