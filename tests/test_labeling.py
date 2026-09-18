from pathlib import Path

from todomancer.grouping import Group
from todomancer.labeling import compute_item_scores, label_group, summarize_groups
from todomancer.scanner import TodoItem


def make_item(marker: str, text: str, mtime: float = 0.0, file: str = "f.py") -> TodoItem:
    return TodoItem(file=Path(file), line=1, marker=marker, text=text, context=text, mtime=mtime)


def test_compute_item_scores_marker_weight_ordering():
    fixme = make_item("FIXME", "a", mtime=100.0)
    hack = make_item("HACK", "b", mtime=100.0)
    todo = make_item("TODO", "c", mtime=100.0)
    xxx = make_item("XXX", "d", mtime=100.0)

    scores = compute_item_scores([fixme, hack, todo, xxx])

    assert scores[id(fixme)] == scores[id(hack)] == 3.0
    assert scores[id(todo)] == 2.0
    assert scores[id(xxx)] == 1.0


def test_compute_item_scores_age_is_tie_breaker_within_same_marker():
    older = make_item("TODO", "a", mtime=0.0)
    newer = make_item("TODO", "b", mtime=100.0)

    scores = compute_item_scores([older, newer])

    assert scores[id(older)] > scores[id(newer)]
    assert 2.0 <= scores[id(newer)] < scores[id(older)] <= 3.0


def test_compute_item_scores_zero_span_gives_no_age_bonus():
    a = make_item("TODO", "a", mtime=50.0)
    b = make_item("TODO", "b", mtime=50.0)

    scores = compute_item_scores([a, b])

    assert scores[id(a)] == scores[id(b)] == 2.0


def test_compute_item_scores_empty_list():
    assert compute_item_scores([]) == {}


def test_label_group_picks_most_frequent_words():
    group = Group(
        items=[
            make_item("TODO", "refactor the parser module"),
            make_item("TODO", "refactor parser error handling"),
        ]
    )

    label = label_group(group)

    assert "refactor" in label
    assert "parser" in label


def test_label_group_filters_stopwords_and_short_words():
    group = Group(items=[make_item("TODO", "we need to fix it")])

    label = label_group(group)

    assert "need" not in label
    assert "fix" in label


def test_label_group_empty_when_no_meaningful_words():
    group = Group(items=[make_item("TODO", "is a to")])

    assert label_group(group) == "(unlabeled)"


def test_summarize_groups_score_is_max_of_members():
    minor = make_item("XXX", "cosmetic tweak", mtime=100.0)
    urgent = make_item("FIXME", "security hole", mtime=100.0)
    group = Group(items=[minor, urgent])

    summaries = summarize_groups([group])

    assert summaries[0].score == 3.0


def test_summarize_groups_sorted_by_score_descending():
    low = Group(items=[make_item("XXX", "cosmetic", mtime=100.0)])
    high = Group(items=[make_item("FIXME", "urgent bug", mtime=100.0)])

    summaries = summarize_groups([low, high])

    assert summaries[0].group is high
    assert summaries[1].group is low
    assert summaries[0].score >= summaries[1].score
