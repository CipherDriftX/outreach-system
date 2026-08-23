"""State schemas for Outreach OS — pure in-memory, no database.

SignalGraphState: Node 1 discovery graph
LeadResearchState: Node 2 per-lead research subgraph

Every accumulating field has an explicit reducer. Default overwrite
is correct only for single-writer fields.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def _merge_unique_append(existing: list[str], new: list[str]) -> list[str]:
    seen = set(existing)
    return existing + [item for item in new if item not in seen and not seen.add(item)]


def _merge_set_union(existing: set[str], new: set[str]) -> set[str]:
    return existing | new


def _merge_novelty(
    existing: dict[str, list[float]], new: dict[str, list[float]]
) -> dict[str, list[float]]:
    merged = dict(existing or {})
    for adapter, history in (new or {}).items():
        merged[adapter] = merged.get(adapter, []) + list(history)
    return merged


def _accumulate_float(a: float, b: float) -> float:
    return (a or 0.0) + (b or 0.0)


def _merge_errors(existing: list[dict], new: list[dict]) -> list[dict]:
    return (existing or []) + (new or [])


def _merge_taxonomy(
    existing: dict[str, Any], new: dict[str, Any]
) -> dict[str, Any]:
    merged = dict(existing or {})
    new_verticals = list(merged.get("verticals", []))
    for v in new.get("verticals", []):
        if v not in new_verticals:
            new_verticals.append(v)
    merged.update(new)
    merged["verticals"] = new_verticals
    return merged


def _merge_signals(existing: list[dict], new: list[dict]) -> list[dict]:
    seen_urls = {s.get("url") for s in existing if s.get("url")}
    result = list(existing)
    for s in new:
        if s.get("url") not in seen_urls:
            seen_urls.add(s.get("url"))
            result.append(s)
    return result


def _merge_leads(existing: list[dict], new: list[dict]) -> list[dict]:
    seen_ids = {l.get("lead_id") for l in existing if l.get("lead_id")}
    result = list(existing)
    for ld in new:
        lid = ld.get("lead_id")
        if lid and lid not in seen_ids:
            seen_ids.add(lid)
            result.append(ld)
    return result


def _merge_facts(existing: list[dict], new: list[dict]) -> list[dict]:
    seen_ids = {f.get("id") for f in existing if f.get("id")}
    result = list(existing)
    for f in new:
        fid = f.get("id")
        if fid and fid not in seen_ids:
            seen_ids.add(fid)
            result.append(f)
    return result


class SignalGraphState(TypedDict, total=False):
    business_id: str
    run_id: str
    thread_id: str

    taxonomy: Annotated[dict[str, Any], _merge_taxonomy]
    active_vertical_index: int

    discovered_signals: Annotated[list[dict], _merge_signals]
    discovered_leads: Annotated[list[dict], _merge_leads]
    seen_urls: Annotated[set[str], _merge_set_union]
    expanded_verticals: Annotated[set[str], _merge_set_union]

    queries_by_vertical: dict[str, list[str]]
    successful_patterns: list[str]
    novelty_history: Annotated[dict[str, list[float]], _merge_novelty]

    current_phase: str
    budget_spent_usd: Annotated[float, _accumulate_float]
    budget_limit_usd: float
    errors: Annotated[list[dict], _merge_errors]
    node_logs: Annotated[list[dict], _merge_errors]
    schema_version: int


def create_signal_state(
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
        "discovered_signals": [],
        "discovered_leads": [],
        "seen_urls": set(),
        "expanded_verticals": set(),
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


class LeadResearchState(TypedDict, total=False):
    lead_id: str
    business_id: str
    lead: dict[str, Any]
    signal: dict[str, Any]

    taxonomy: dict[str, Any]
    track_a_done: bool
    track_b_done: bool

    discovered_facts: Annotated[list[dict], _merge_facts]
    dossier: dict[str, Any]
    gap_hypothesis: dict[str, Any]

    budget_spent_usd: Annotated[float, _accumulate_float]
    errors: Annotated[list[dict], _merge_errors]
    node_logs: Annotated[list[dict], _merge_errors]
    schema_version: int


def create_lead_state(
    lead_id: str,
    business_id: str,
    lead: dict[str, Any],
    signal: dict[str, Any],
) -> dict:
    return {
        "lead_id": lead_id,
        "business_id": business_id,
        "lead": lead,
        "signal": signal,
        "taxonomy": {},
        "track_a_done": False,
        "track_b_done": False,
        "discovered_facts": [],
        "dossier": {},
        "gap_hypothesis": {},
        "budget_spent_usd": 0.0,
        "errors": [],
        "node_logs": [],
        "schema_version": 1,
    }