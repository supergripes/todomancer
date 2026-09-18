# todomancer

Scans a codebase for `TODO`/`FIXME`/`HACK`/`XXX` comments, groups them by
semantic similarity, and produces a report sorted by priority.

## How it works

1. **Scan**: recursive directory walk (respects `.gitignore` when
   present), extracting markers via regex from the main comment styles
   (`//`, `#`, `/* */`).
2. **Embedding**: each TODO becomes a vector using
   [sentence-transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`,
   local, no API key).
3. **Grouping**: greedy, similar TODOs (cosine similarity above the
   threshold) join the same group, and the centroid is updated as it goes.
4. **Label and priority**: most frequent keyword per group, priority
   score from marker severity plus file age.
5. **Report**: terminal output with [rich](https://rich.readthedocs.io/),
   optionally exported to Markdown.

## Install

```bash
pip install -e .
```

## Usage

```bash
todomancer /path/to/project
todomancer . --output report.md
todomancer . --threshold 0.45  # more permissive grouping threshold
```

## Stack

- [typer](https://typer.tiangolo.com/): CLI
- [sentence-transformers](https://www.sbert.net/): local embeddings
- [rich](https://rich.readthedocs.io/): terminal output

Everything else is stdlib.
