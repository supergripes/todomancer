"""Walks a codebase directory and extracts TODO/FIXME/HACK/XXX comments."""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path

MARKERS = ("FIXME", "HACK", "TODO", "XXX")

MARKER_RE = re.compile(r"\b(" + "|".join(MARKERS) + r")\b:?\s*(.*)", re.IGNORECASE)

# Extensions worth scanning for comments. Deliberately not mapping one
# comment style per language: the same generic scanner (//, #, /* */) is
# applied to every whitelisted file.
DEFAULT_EXTENSIONS = {
    ".py", ".pyi",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".go", ".rs",
    ".java", ".kt", ".kts", ".scala",
    ".c", ".h", ".cpp", ".cc", ".hpp", ".hh",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".m", ".mm",
    ".sh", ".bash", ".zsh",
    ".yml", ".yaml", ".toml",
    ".sql",
    ".dart",
}

CONTEXT_RADIUS = 2

ALWAYS_IGNORED_DIRS = {".git"}


@dataclass
class TodoItem:
    file: Path
    line: int
    marker: str
    text: str
    context: str
    mtime: float


class GitignoreMatcher:
    """Minimal .gitignore matcher, based on fnmatch (stdlib only).

    Covers the common cases (wildcards, `/`-anchoring, directory-only
    patterns with a trailing `/`, negation with `!`) but not the full git
    semantics: good enough for filtering a scan, not a real
    `git check-ignore`.
    """

    def __init__(self, root: Path):
        self.root = root
        self.patterns: list[tuple[str, bool, bool, bool]] = []
        gitignore_path = root / ".gitignore"
        if gitignore_path.is_file():
            for raw_line in gitignore_path.read_text(errors="ignore").splitlines():
                line = raw_line.rstrip()
                if not line or line.startswith("#"):
                    continue
                negate = line.startswith("!")
                if negate:
                    line = line[1:]
                dir_only = line.endswith("/")
                if dir_only:
                    line = line[:-1]
                anchored = line.startswith("/")
                if anchored:
                    line = line[1:]
                if not line:
                    continue
                self.patterns.append((line, negate, dir_only, anchored))

    def is_ignored(self, path: Path, is_dir: bool) -> bool:
        rel = path.relative_to(self.root)
        rel_str = str(rel)
        parts = rel.parts
        ignored = False
        for pattern, negate, dir_only, anchored in self.patterns:
            if dir_only and not is_dir:
                continue
            if anchored:
                matched = fnmatch.fnmatch(rel_str, pattern)
            else:
                matched = fnmatch.fnmatch(rel_str, pattern) or any(
                    fnmatch.fnmatch(part, pattern) for part in parts
                )
            if matched:
                ignored = not negate
        return ignored


def _iter_candidate_files(root: Path, extensions: set[str]) -> list[Path]:
    matcher = GitignoreMatcher(root)
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            d
            for d in dirnames
            if d not in ALWAYS_IGNORED_DIRS
            and not matcher.is_ignored(current / d, is_dir=True)
        ]
        for filename in filenames:
            file_path = current / filename
            if file_path.suffix.lower() not in extensions:
                continue
            if matcher.is_ignored(file_path, is_dir=False):
                continue
            files.append(file_path)
    return files


def _find_comment_segment(line: str, in_block: bool) -> tuple[str | None, bool, str]:
    """Returns (comment_segment_or_None, new_in_block_state, line_remainder).

    `line_remainder` is the part of the line after a `*/` block that closed
    on the same line (so scanning can continue further, if needed).
    """
    if in_block:
        end_idx = line.find("*/")
        if end_idx == -1:
            return line, True, ""
        return line[:end_idx], False, line[end_idx + 2 :]

    idx_slash = line.find("//")
    idx_hash = line.find("#")
    idx_block = line.find("/*")
    candidates = [
        (idx, kind)
        for idx, kind in ((idx_slash, "//"), (idx_hash, "#"), (idx_block, "/*"))
        if idx != -1
    ]
    if not candidates:
        return None, False, ""

    idx, kind = min(candidates, key=lambda c: c[0])
    if kind == "/*":
        end_idx = line.find("*/", idx + 2)
        if end_idx == -1:
            return line[idx + 2 :], True, ""
        return line[idx + 2 : end_idx], False, line[end_idx + 2 :]

    return line[idx + len(kind) :], False, ""


def _scan_file(path: Path, root: Path) -> list[TodoItem]:
    try:
        text = path.read_text(errors="ignore")
    except (OSError, UnicodeDecodeError):
        return []

    lines = text.splitlines()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0

    items: list[TodoItem] = []
    in_block = False
    for line_no, line in enumerate(lines, start=1):
        remainder = line
        while True:
            segment, in_block, remainder = _find_comment_segment(remainder, in_block)
            if segment is None:
                break
            match = MARKER_RE.search(segment)
            if match:
                marker = match.group(1).upper()
                comment_text = match.group(2).strip()
                start = max(0, line_no - 1 - CONTEXT_RADIUS)
                end = min(len(lines), line_no + CONTEXT_RADIUS)
                context = "\n".join(lines[start:end])
                try:
                    rel_path = path.relative_to(root)
                except ValueError:
                    rel_path = path
                items.append(
                    TodoItem(
                        file=rel_path,
                        line=line_no,
                        marker=marker,
                        text=comment_text,
                        context=context,
                        mtime=mtime,
                    )
                )
            if not remainder:
                break
    return items


def scan_directory(
    root: str | Path, extensions: set[str] | None = None
) -> list[TodoItem]:
    """Walks `root` recursively and returns all the TodoItems found."""
    root = Path(root).resolve()
    exts = extensions or DEFAULT_EXTENSIONS
    items: list[TodoItem] = []
    for file_path in _iter_candidate_files(root, exts):
        items.extend(_scan_file(file_path, root))
    return items
