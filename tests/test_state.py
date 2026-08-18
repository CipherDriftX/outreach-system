"""State reducer tests — the merge-semantics contract.

Per langgraph-engineering-patterns: if two branches write the same field in
the same superstep, the reducer defines what happens. These tests lock the
merge semantics in place.
"""

from src.state import (
    _merge_errors,
    _merge_novelty,
    _merge_set_union,
    _merge_unique_append,
)


def test_unique_append_dedups():
    result = _merge_unique_append(["a", "b"], ["b", "c"])
    assert result == ["a", "b", "c"]


def test_unique_append_idempotent():
    # Writers returning the accumulated list must not double it
    existing = ["a", "b"]
    result = _merge_unique_append(existing, ["a", "b", "c"])
    assert result == ["a", "b", "c"]
    result2 = _merge_unique_append(result, result)
    assert result2 == ["a", "b", "c"]


def test_set_union():
    assert _merge_set_union({"a"}, {"b"}) == {"a", "b"}
    assert _merge_set_union({"a", "b"}, {"b", "c"}) == {"a", "b", "c"}


def test_novelty_history_accumulates_per_adapter():
    existing = {"reddit": [0.5]}
    new = {"reddit": [0.2], "twitter": [0.8]}
    result = _merge_novelty(existing, new)
    assert result["reddit"] == [0.5, 0.2]
    assert result["twitter"] == [0.8]


def test_errors_append():
    assert _merge_errors([{"a": 1}], [{"b": 2}]) == [{"a": 1}, {"b": 2}]