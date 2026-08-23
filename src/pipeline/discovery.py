"""Stage 1: Runs the recursive Node 1 LangGraph, extracts signals.

This is a thin wrapper. The real work happens in src/graph.py's
LangGraph — taxonomy building, dual-track discovery, frontier discipline,
saturation, split detection, LLM triage. All in-memory.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import structlog

from src.adapters.signals.registry import all_adapters
from src.llm.cascade import complete_tier

logger = structlog.get_logger(__name__)

ICP_ROOT = (
    "Businesses with painful operational processes that are candidates "
    "for autonomous AI execution"
)


async def _run_graph(
    business_id: str, run_id: str, thread_id: str,
    taxonomy: dict | None, budget: float,
) -> dict:
    from src.graph import run_signal_discovery
    return await run_signal_discovery(
        business_id=business_id, run_id=run_id, thread_id=thread_id,
        taxonomy=taxonomy, budget_limit_usd=budget,
    )


def discover(
    icp_root: str = ICP_ROOT,
    limit_adapters: list[str] | None = None,
) -> dict[str, Any]:
    import uuid

    run_id = str(uuid.uuid4())
    thread_id = f"signal-{run_id[:8]}"

    taxonomy = None
    try:
        from src.nodes.signal.taxonomy import build_taxonomy
        taxonomy = build_taxonomy(icp_root, "")
        if taxonomy and taxonomy.get("verticals"):
            taxonomy["verticals"] = taxonomy["verticals"][:3]
    except Exception:
        pass

    try:
        final = asyncio.run(_run_graph("plarix", run_id, thread_id, taxonomy, 5.0))
    except Exception as exc:
        logger.error("graph_failed", error=str(exc))
        return {"signals": [], "leads": [], "error": str(exc)}

    signals = final.get("discovered_signals", [])
    leads = final.get("discovered_leads", [])

    per_adapter_rounds = {}
    per_adapter_novelty = {}
    for s in signals:
        name = s.get("source_name", "unknown")
        per_adapter_rounds[name] = per_adapter_rounds.get(name, 0) + 1
    for k, v in final.get("novelty_history", {}).items():
        per_adapter_novelty[k] = v

    for s in signals:
        s.setdefault("triage_score", 0)
        s.setdefault("triage_reason", "")

    return {
        "signals": signals,
        "leads": leads,
        "taxonomy": final.get("taxonomy", {}),
        "per_adapter_rounds": per_adapter_rounds,
        "per_adapter_novelty": per_adapter_novelty,
    }