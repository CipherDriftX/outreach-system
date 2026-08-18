"""SignalGraphState — the typed contract for Node 1's discovery graph.

Per langgraph-engineering-patterns: every accumulating field gets an explicit
reducer. Default overwrite is correct for single-writer fields only.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict


def _merge_unique_append(existing: list[str], new: list[str]) -> list[str]:
    seen = set(existing)
    return existing + [item for item in new if item not in seen and not seen.add(item)]


def _merge_set_union(existing: set[str], new: set[str]) -> set[str]:
    return existing | new


def _merge_novelty(existing: dict[str, list[float]], new: dict[str, list[float]]) -> dict[str, list[float]]:
    merged = dict(existing or {})
    for adapter, history in (new or {}).items():
        merged[adapter] = merged.get(adapter, []) + list(history)
    return merged


def _accumulate_float(a: float, b: float) -> float:
    return (a or 0.0) + (b or 0.0)


def _merge_errors(existing: list[dict], new: list[dict]) -> list[dict]:
    return (existing or []) + (new or [])


class SignalGraphState(TypedDict, total=False):
    # Identity
    business_id: str
    run_id: str
    thread_id: str

    # Taxonomy
    taxonomy: dict[str, Any]
    active_vertical_index: int

    # Discovery accumulation
    discovered_signal_ids: Annotated[list[str], _merge_unique_append]
    discovered_lead_ids: Annotated[list[str], _merge_unique_append]
    triaged_signal_ids: Annotated[set[str], _merge_set_union]
    expanded_vertical_labels: Annotated[set[str], _merge_set_union]

    # Frontier: queries issued per vertical (never reissue)
    queries_by_vertical: dict[str, list[str]]
    successful_patterns: list[str]

    # Novelty tracking per adapter
    novelty_history: Annotated[dict[str, list[float]], _merge_novelty]

    # Control flow
    current_phase: str  # "discovering" | "saturated" | "splitting" | "done"

    # Budget
    budget_spent_usd: Annotated[float, _accumulate_float]
    budget_limit_usd: float

    # Errors
    errors: Annotated[list[dict], _merge_errors]

    # Logs
    node_logs: Annotated[list[dict], _merge_errors]

    # Schema
    schema_version: int


def create_initial_state(
    business_id: str,
    run_id: str,
    thread_id: str,
    taxonomy: dict[str, Any],
    budget_limit_usd: float = 5.0,
) -> dict:
    return {
        "business_id": business_id,
        "run_id": run_id,
        "thread_id": thread_id,
        "taxonomy": taxonomy,
        "active_vertical_index": 0,
        "discovered_signal_ids": [],
        "discovered_lead_ids": [],
        "triaged_signal_ids": set(),
        "expanded_vertical_labels": set(),
        "queries_by_vertical": {},
        "successful_patterns": [],
        "novelty_history": {},
        "current_phase": "discovering",
        "budget_spent_usd": 0.0,
        "budget_limit_usd": budget_limit_usd,
        "errors": [],
        "node_logs": [],
        "schema_version": 1,
    }


def migrate_state(state: dict) -> dict:
    version = state.get("schema_version", 0)
    if version < 1:
        state.setdefault("novelty_history", {})
        state.setdefault("expanded_vertical_labels", set())
        state.setdefault("triaged_signal_ids", set())
        state.setdefault("queries_by_vertical", {})
        state.setdefault("successful_patterns", [])
        version = 1
    state["schema_version"] = version
    return state