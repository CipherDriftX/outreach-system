"""graph.py — Node 1 LangGraph: Recursive Signal Discovery.

One pass per vertical. Triage happens once after all verticals are explored.
The recursive architecture (taxonomy → dual-track → frontier → saturation)
runs per-vertical within discover_vertical. Split detection deferred to v2.
"""

from __future__ import annotations

import json as _json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.state import SignalGraphState, create_signal_state

logger = structlog.get_logger(__name__)

ICP_ROOT = "Businesses with painful operational processes that are candidates for autonomous AI execution"


def _init_taxonomy(state: SignalGraphState) -> dict:
    from src.llm.cascade import complete_tier

    taxonomy = state.get("taxonomy", {})
    if taxonomy and taxonomy.get("verticals"):
        return {}

    root = taxonomy.get("root") or ICP_ROOT
    prompt = f"""Design a signal-discovery taxonomy.

ICP: "{root}"

Produce exactly 3 depth-1 verticals. Each is a CATEGORY OF PUBLIC SIGNAL.
For each: label (snake_case), description, 2 intent patterns, adapter names
(focus on hackernews, github, reddit, stackexchange).

Return ONLY: {{"verticals":[{{"label":"...","description":"...","intent_patterns":["..."],"adapters":["hackernews"]}}]}}"""

    result = complete_tier("frontier", prompt)
    raw = result.get("content", "{}")
    try:
        data = _json.loads(raw)
    except Exception:
        if "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        try:
            data = _json.loads(raw)
        except Exception:
            data = {"verticals": _default_verticals()}

    verticals = data.get("verticals", _default_verticals())[:3]
    new_tax = {"root": root, "verticals": verticals, "llm_seed": True}
    print(f"[graph] taxonomy: {[v['label'] for v in verticals]}", flush=True)
    return {"taxonomy": new_tax, "budget_spent_usd": result.get("cost_usd", 0.0)}


def _default_verticals() -> list[dict]:
    return [
        {"label": "forum_posts", "description": "Help-seeking posts", "intent_patterns": ["looking for", "struggling with"], "adapters": ["hackernews", "reddit"]},
        {"label": "dev_activity", "description": "GitHub issues, feature requests", "intent_patterns": ["automation tool", "wish we had"], "adapters": ["github"]},
        {"label": "marketplace_gigs", "description": "Explicit needs with budgets", "intent_patterns": ["need someone to", "looking for developer"], "adapters": ["upwork"]},
    ]


def _select_vertical(state: SignalGraphState) -> dict:
    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])
    expanded = state.get("expanded_verticals", set())
    for i, v in enumerate(verticals):
        if v.get("label") not in expanded:
            return {"active_vertical_index": i, "expanded_verticals": {v["label"]}}
    return {"current_phase": "done"}


def _discover_vertical(state: SignalGraphState) -> dict:
    from src.adapters.signals.registry import all_adapters

    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])
    idx = state.get("active_vertical_index", 0)
    if idx >= len(verticals):
        return {}

    vertical = verticals[idx]
    label = vertical.get("label", "unknown")
    patterns = vertical.get("intent_patterns", [])
    adapter_names = vertical.get("adapters", [])
    if not adapter_names:
        adapter_names = ["hackernews", "github"]

    seen = state.get("seen_urls", set())
    all_raw = []
    per_adapter_rounds = {}

    for adapter in all_adapters():
        if adapter.name not in adapter_names:
            continue
        try:
            for pattern in patterns[:1]:
                raw = adapter.search(pattern)
                for s in raw:
                    s["matched_pattern"] = pattern
                all_raw.extend(raw)
                per_adapter_rounds[adapter.name] = len(raw)
        except Exception:
            logger.warning("adapter_search_failed", adapter=adapter.name)

    deduped = []
    for s in all_raw:
        url = s["url"]
        if url not in seen:
            seen.add(url)
            s["signal_id"] = str(uuid.uuid4())
            s["captured_at"] = datetime.now(timezone.utc).isoformat()
            deduped.append(s)

    print(f"[graph] {label}: {len(deduped)} new from {len(all_raw)} raw ({', '.join(f'{a}:{c}' for a,c in per_adapter_rounds.items())})", flush=True)
    return {"discovered_signals": deduped, "seen_urls": seen}


def _triage_all(state: SignalGraphState) -> dict:
    from src.llm.cascade import complete_tier

    all_signals = state.get("discovered_signals", [])
    if not all_signals:
        return {"discovered_leads": []}

    untriaged = [s for s in all_signals if s.get("triage_score") is None]
    if not untriaged:
        all_leads = _extract_leads(all_signals)
        return {"discovered_leads": all_leads}

    taxonomy = state.get("taxonomy", {})
    icp_root = taxonomy.get("root", ICP_ROOT)
    print(f"[graph] triaging {len(untriaged)} signals in batches of 10", flush=True)

    for start in range(0, len(untriaged), 10):
        batch = untriaged[start : start + 10]
        lines = "\n".join(f"{i}: [{s.get('source_name')}] {s.get('raw_text','')[:100]}" for i, s in enumerate(batch))
        prompt = f"""Score each signal 0-3 on relevance to: "{icp_root}"
0=irrelevant 1=potential 2=relevant 3=strong match.
Return ONLY: {{"scores":[{{"idx":0,"score":2,"reasoning":"..."}}]}}
{lines}"""
        try:
            r = complete_tier("cheap", prompt)
            data = _json.loads(r.get("content", "{}"))
            for e in data.get("scores", []):
                idx = int(e.get("idx", -1))
                if 0 <= idx < len(batch):
                    batch[idx]["triage_score"] = max(0, min(3, int(e.get("score", 0))))
                    batch[idx]["triage_reason"] = e.get("reasoning", "")
        except Exception:
            for s in batch:
                s.setdefault("triage_score", 0)

    all_leads = _extract_leads(all_signals)
    print(f"[graph] triage done: {len(all_leads)} leads from {len(all_signals)} signals", flush=True)
    return {"discovered_leads": all_leads, "discovered_signals": all_signals}


def _extract_leads(signals: list[dict]) -> list[dict]:
    leads = []
    for s in signals:
        score = s.get("triage_score", 0)
        if score >= 1:
            leads.append({
                "lead_id": str(uuid.uuid4()),
                "signal_id": s.get("signal_id"),
                "triage_score": score,
                "triage_reason": s.get("triage_reason", ""),
                "company_name": s.get("author_handle", ""),
                "contact_name": s.get("author_handle", ""),
                "signal": dict(s),
            })
    return leads


def _check_saturation(state: SignalGraphState) -> dict:
    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])
    expanded = state.get("expanded_verticals", set())
    remaining = [v for v in verticals if v.get("label") not in expanded]
    if remaining:
        return {"current_phase": "discovering"}
    return {}


def _fan_out(state: SignalGraphState) -> dict:
    return {}


def route_after_saturation(state: SignalGraphState) -> list[str]:
    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])
    expanded = state.get("expanded_verticals", set())
    remaining = [v for v in verticals if v.get("label") not in expanded]
    return ["select_vertical"] if remaining else ["triage_all"]


def build_signal_graph() -> StateGraph:
    g = StateGraph(SignalGraphState)
    g.add_node("init_taxonomy", _init_taxonomy)
    g.add_node("select_vertical", _select_vertical)
    g.add_node("discover_vertical", _discover_vertical)
    g.add_node("triage_all", _triage_all)
    g.add_node("check_saturation", _check_saturation)
    g.add_node("fan_out", _fan_out)

    g.add_edge(START, "init_taxonomy")
    g.add_edge("init_taxonomy", "select_vertical")
    g.add_edge("select_vertical", "discover_vertical")
    g.add_edge("discover_vertical", "check_saturation")
    g.add_conditional_edges("check_saturation", route_after_saturation, ["select_vertical", "triage_all"])
    g.add_edge("triage_all", "fan_out")
    g.add_edge("fan_out", END)
    return g


def compile_signal_graph(checkpointer=None):
    return build_signal_graph().compile(checkpointer=checkpointer or MemorySaver())


async def run_signal_discovery(
    business_id: str = "plarix", run_id: str = "", thread_id: str = "",
    taxonomy: dict | None = None, budget_limit_usd: float = 5.0,
) -> dict:
    if run_id == "":
        run_id = str(uuid.uuid4())
    if thread_id == "":
        thread_id = f"signal-{run_id[:8]}"
    if taxonomy is None:
        taxonomy = {"root": ICP_ROOT, "verticals": _default_verticals()}

    app = compile_signal_graph()
    initial = create_signal_state(business_id=business_id, run_id=run_id, thread_id=thread_id, taxonomy=taxonomy, budget_limit_usd=budget_limit_usd)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 30}
    final = await app.ainvoke(initial, config=config)
    return dict(final)