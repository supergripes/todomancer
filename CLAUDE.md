# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

`todomancer` is intentionally small in scope, a weekend portfolio project.
Keep changes minimal and focused: flag anything that would meaningfully grow
the project instead of just doing it.

It scans a codebase for `TODO`/`FIXME`/`HACK`/`XXX` comments, groups them by
semantic similarity using local embeddings, and reports them sorted by
priority. **All embedding runs locally, no external LLM/API calls in any
phase.** Don't reintroduce a network dependency (a hosted embedding API, an
LLM call for labeling, etc.) without the user explicitly asking for it.

## Architecture

- [src/todomancer/cli.py](src/todomancer/cli.py): typer argument parsing
  only, wires the pipeline below. No logic of its own.
- [src/todomancer/scanner.py](src/todomancer/scanner.py): recursive
  directory walk, a minimal stdlib-only `.gitignore` matcher, and regex
  extraction of markers from `//`, `#`, `/* */` comments (same generic
  scanner applied to every whitelisted extension, not one style per
  language).
- [src/todomancer/grouping.py](src/todomancer/grouping.py): embedding via
  sentence-transformers (`all-MiniLM-L6-v2`, imported lazily so importing
  this module doesn't require torch) and greedy grouping by cosine
  similarity against each group's running-mean centroid.
- [src/todomancer/labeling.py](src/todomancer/labeling.py): group labels
  from word frequency (`Counter`, no TF-IDF/sklearn) and priority scoring
  (marker weight plus a normalized file-age bonus). A group's score is the
  max of its members, not the average.
- [src/todomancer/report.py](src/todomancer/report.py): rich terminal
  output (fixed priority color thresholds, clickable `file://` links) and
  Markdown export.

## Conventions

- Three runtime dependencies only: `typer`, `sentence-transformers`,
  `rich`, plus stdlib. `pytest` is a dev-only extra. Don't add a new
  dependency without asking first.
- No em dashes anywhere: prose, docs, commit messages, code comments.
- No `Co-Authored-By` trailer (or similar AI attribution) in commits or PR
  descriptions. Claude is used on this project day to day; that disclosure
  belongs here, in project docs, not in commit metadata attributing
  authorship of individual changes.
- Only commit or push when explicitly asked.
- The grouping threshold defaults to 0.6 but is meant to be tuned per
  repo: with `all-MiniLM-L6-v2`, genuinely related short TODO comments
  often score around 0.4 to 0.5 cosine similarity, not 0.6+. Don't treat
  0.6 as correct by default when debugging grouping quality.

## Build & test

```bash
pip install -e ".[test]"
pytest
```

```bash
todomancer /path/to/project
todomancer . --output report.md
```
