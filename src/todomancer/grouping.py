"""TODO embedding and greedy grouping by semantic similarity."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .scanner import TodoItem

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_THRESHOLD = 0.6

_model = None
_model_name = None


def _get_model(model_name: str = DEFAULT_MODEL_NAME):
    global _model, _model_name
    if _model is None or _model_name != model_name:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(model_name)
        _model_name = model_name
    return _model


def _embedding_text(item: TodoItem) -> str:
    return item.text or item.context


def embed_items(
    items: list[TodoItem], model_name: str = DEFAULT_MODEL_NAME
) -> np.ndarray:
    """Turns each TodoItem into a vector. Returns an (n_items, dim) array."""
    if not items:
        return np.empty((0, 0))
    model = _get_model(model_name)
    texts = [_embedding_text(item) for item in items]
    embeddings = model.encode(texts, convert_to_numpy=True)
    return np.asarray(embeddings)


@dataclass
class Group:
    items: list[TodoItem] = field(default_factory=list)
    centroid: np.ndarray | None = None

    def add(self, item: TodoItem, vec: np.ndarray) -> None:
        self.items.append(item)
        n = len(self.items)
        self.centroid = self.centroid + (vec - self.centroid) / n


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def group_items(
    items: list[TodoItem],
    embeddings: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[Group]:
    """Greedily groups the TODOs in the order they appear.

    For each TODO, computes the cosine similarity against the centroid of
    every group created so far; if the best one is above `threshold`, adds
    it to that group (updating the centroid as an incremental mean),
    otherwise opens a new group.
    """
    groups: list[Group] = []
    for item, vec in zip(items, embeddings):
        best_group: Group | None = None
        best_sim = -1.0
        for group in groups:
            sim = _cosine_similarity(vec, group.centroid)
            if sim > best_sim:
                best_sim = sim
                best_group = group

        if best_group is not None and best_sim >= threshold:
            best_group.add(item, vec)
        else:
            groups.append(Group(items=[item], centroid=vec.copy()))

    return groups


def group_todos(
    items: list[TodoItem],
    threshold: float = DEFAULT_THRESHOLD,
    model_name: str = DEFAULT_MODEL_NAME,
) -> list[Group]:
    """Shortcut: embedding + grouping in a single step."""
    if not items:
        return []
    embeddings = embed_items(items, model_name=model_name)
    return group_items(items, embeddings, threshold=threshold)
