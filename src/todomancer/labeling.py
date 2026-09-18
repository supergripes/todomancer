"""Group labels (most frequent words) and priority scoring."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .grouping import Group
from .scanner import TodoItem

MARKER_WEIGHT = {
    "FIXME": 3,
    "HACK": 3,
    "TODO": 2,
    "XXX": 1,
}
DEFAULT_MARKER_WEIGHT = 1

WORD_RE = re.compile(r"[a-zA-Z']+")

# Minimal stopword list: filler words too common to make a useful label.
# No TF-IDF, no sklearn: just a Counter.
STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is",
    "this", "that", "it", "with", "be", "are", "we", "need", "needs",
    "should", "when", "here", "there", "not", "but", "as", "at", "by",
    "from", "was", "were", "will", "just", "still", "actually", "really",
    "todo", "fixme", "hack", "xxx", "note",
}


@dataclass
class GroupSummary:
    group: Group
    label: str
    score: float


def compute_item_scores(items: list[TodoItem]) -> dict[int, float]:
    """Score for each TODO: marker weight + normalized age bonus.

    The age bonus is in [0, 1] (1 = the oldest file among those passed in,
    0 = the most recent) and acts as a tie-breaker between TODOs sharing a
    marker; the marker weight remains the dominant factor.
    """
    if not items:
        return {}

    mtimes = [item.mtime for item in items]
    oldest, newest = min(mtimes), max(mtimes)
    span = newest - oldest

    scores: dict[int, float] = {}
    for item in items:
        marker_weight = MARKER_WEIGHT.get(item.marker, DEFAULT_MARKER_WEIGHT)
        age_bonus = (newest - item.mtime) / span if span > 0 else 0.0
        scores[id(item)] = marker_weight + age_bonus
    return scores


def label_group(group: Group, top_n: int = 3) -> str:
    """Label = most frequent words in the group (Counter, no TF-IDF)."""
    counter: Counter[str] = Counter()
    for item in group.items:
        words = WORD_RE.findall((item.text or item.context).lower())
        for word in words:
            if len(word) < 3 or word in STOPWORDS:
                continue
            counter[word] += 1

    if not counter:
        return "(unlabeled)"
    return " / ".join(word for word, _ in counter.most_common(top_n))


def summarize_groups(groups: list[Group]) -> list[GroupSummary]:
    """Labels and assigns priority to each group, sorted by priority.

    A group's score is the max of its TODOs' scores: a single urgent
    FIXME is enough to bring the whole group to the top.
    """
    all_items = [item for group in groups for item in group.items]
    item_scores = compute_item_scores(all_items)

    summaries = [
        GroupSummary(
            group=group,
            label=label_group(group),
            score=max((item_scores[id(item)] for item in group.items), default=0.0),
        )
        for group in groups
    ]
    summaries.sort(key=lambda s: s.score, reverse=True)
    return summaries
