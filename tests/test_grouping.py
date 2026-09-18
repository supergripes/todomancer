from pathlib import Path

import numpy as np

from todomancer.grouping import _cosine_similarity, group_items
from todomancer.scanner import TodoItem


def make_item(text: str) -> TodoItem:
    return TodoItem(file=Path("f.py"), line=1, marker="TODO", text=text, context=text, mtime=0.0)


def test_cosine_similarity_identical_vectors_is_one():
    v = np.array([1.0, 2.0, 3.0])
    assert _cosine_similarity(v, v) == 1.0


def test_cosine_similarity_orthogonal_vectors_is_zero():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_opposite_vectors_is_minus_one():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert _cosine_similarity(a, b) == -1.0


def test_cosine_similarity_zero_vector_is_zero_not_nan():
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 0.0])
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_is_magnitude_independent():
    a = np.array([1.0, 0.0])
    b = np.array([50.0, 0.0])
    assert _cosine_similarity(a, b) == 1.0


def test_group_items_merges_similar_vectors():
    items = [make_item("a"), make_item("b"), make_item("c"), make_item("d")]
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.98, 0.02],
            [0.0, 1.0],
            [0.05, 0.95],
        ]
    )

    groups = group_items(items, embeddings, threshold=0.9)

    assert len(groups) == 2
    assert {it.text for it in groups[0].items} == {"a", "b"}
    assert {it.text for it in groups[1].items} == {"c", "d"}


def test_group_items_keeps_dissimilar_vectors_separate():
    items = [make_item("a"), make_item("b")]
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])

    groups = group_items(items, embeddings, threshold=0.5)

    assert len(groups) == 2


def test_group_items_threshold_is_inclusive():
    items = [make_item("a"), make_item("b")]
    # cosine similarity between these two unit vectors is exactly 0.6.
    embeddings = np.array([[1.0, 0.0], [0.6, 0.8]])

    groups = group_items(items, embeddings, threshold=0.6)

    assert len(groups) == 1


def test_group_items_centroid_is_incremental_mean():
    items = [make_item("a"), make_item("b"), make_item("c")]
    embeddings = np.array([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])

    groups = group_items(items, embeddings, threshold=0.5)

    assert len(groups) == 1
    np.testing.assert_allclose(groups[0].centroid, [2.0, 0.0])


def test_group_items_picks_the_most_similar_group():
    items = [make_item("seed_a"), make_item("seed_b"), make_item("query")]
    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 1.0],
            [0.9, 0.1, 0.1],
        ]
    )

    groups = group_items(items, embeddings, threshold=0.3)

    seed_a_group = next(g for g in groups if items[0] in g.items)
    assert items[2] in seed_a_group.items


def test_group_items_empty_input_returns_empty_list():
    assert group_items([], np.empty((0, 2))) == []
