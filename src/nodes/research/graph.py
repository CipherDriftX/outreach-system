"""Node 2 — per-lead research subgraph. Pure in-memory.

One instance per lead that cleared triage. Runs:
taxonomy -> track_a -> track_b -> grade_evidence -> compact -> gap -> finalize

Each lead fails alone. No database. Everything accumulated in state.
"""

from __future__ import annotations

from typing import Annotated, Any

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.state import LeadResearchState, create_lead_state

logger = structlog.get_logger(__name__)


def _build_taxonomy(state: LeadResearchState) -> dict:
    from src.nodes.research.taxonomy import build_lead_taxonomy

    lead = state.get("lead", {})
    signal = state.get("signal", {})
    taxonomy = build_lead_taxonomy(lead, signal)
    return {
        "taxonomy": taxonomy,
        "budget_spent_usd": taxonomy.get("cost_usd", 0.0),
    }


def _track_a(state: LeadResearchState) -> dict:
    from src.adapters.enrichment.web_search import WebSearchEnrichment
    from uuid import uuid4

    lead = state.get("lead", {})
    signal = state.get("signal", {})

    enrichment = WebSearchEnrichment()
    try:
        result = enrichment.enrich(lead, signal)
    except Exception:
        result = {"company_name": lead.get("company_name"), "contact_name": lead.get("contact_name"), "facts": []}

    facts = []
    for f in result.get("facts", []):
        fid = str(uuid4())
        facts.append({
            "id": fid, "fact_type": f.get("fact_type", "observation"),
            "track": "A", "fact": f.get("fact", "")[:2000],
            "source_url": f.get("source_url"),
            "observed_at": f.get("observed_at"),
            "corroboration_count": 1, "recency_days": None,
        })

    if result.get("company_name"):
        lead["company_name"] = result["company_name"]
    if result.get("contact_name"):
        lead["contact_name"] = result["contact_name"]

    return {
        "discovered_facts": facts,
        "track_a_done": True,
        "lead": lead,
        "node_logs": [{"node_name": "track_a", "lead_id": state["lead_id"], "input_summary": {"facts": len(facts)}}],
    }


def _track_b(state: LeadResearchState) -> dict:
    from src.nodes.research.track_b import walk_relationships
    from uuid import uuid4

    signal = state.get("signal", {})
    facts = state.get("discovered_facts", [])

    extra = []
    try:
        tb_result = walk_relationships(signal, facts)
        for direction in tb_result.get("research_directions", [])[:3]:
            if direction:
                fid = str(uuid4())
                extra.append({
                    "id": fid, "fact_type": "relationship_context",
                    "track": "B", "fact": direction,
                    "source_url": signal.get("url"),
                    "observed_at": None, "corroboration_count": 1, "recency_days": None,
                })
    except Exception:
        pass

    return {
        "discovered_facts": extra,
        "track_b_done": True,
        "node_logs": [{"node_name": "track_b", "lead_id": state["lead_id"], "input_summary": {"extra": len(extra)}}],
    }


def _grade_evidence(state: LeadResearchState) -> dict:
    from src.nodes.research.evidence import grade_fact

    all_facts = state.get("discovered_facts", [])
    for f in all_facts:
        g = grade_fact(f)
        f["grade"] = g["grade"]
        f["axis_scores"] = g["axis_scores"]

    return {
        "discovered_facts": all_facts,
    }


def _compact(state: LeadResearchState) -> dict:
    from src.nodes.research.compaction import compact_lead

    lead = state.get("lead", {})
    facts = state.get("discovered_facts", [])
    dossier = compact_lead(lead, facts)
    return {
        "dossier": dossier,
        "budget_spent_usd": dossier.get("cost_usd", 0.0),
    }


def _generate_gap(state: LeadResearchState) -> dict:
    from src.nodes.research.gap import generate_gap_hypothesis
    from uuid import uuid4

    signal = state.get("signal", {})
    facts = state.get("discovered_facts", [])

    try:
        result = generate_gap_hypothesis(signal, facts)
    except Exception:
        result = {"hypothesis": "", "cost_usd": 0.0}

    hypothesis = result.get("hypothesis", "")
    if hypothesis:
        fid = str(uuid4())
        gap_fact = {
            "id": fid, "fact_type": "gap_hypothesis", "track": "A",
            "fact": hypothesis, "source_url": signal.get("url"),
            "observed_at": None, "corroboration_count": 1, "recency_days": None,
        }
    else:
        gap_fact = None

    return {
        "gap_hypothesis": {"hypothesis": hypothesis, "fact_id": gap_fact["id"] if gap_fact else None},
        "discovered_facts": [gap_fact] if gap_fact else [],
        "budget_spent_usd": result.get("cost_usd", 0.0),
    }


def _finalize(state: LeadResearchState) -> dict:
    return {
        "node_logs": [{"node_name": "finalize", "lead_id": state["lead_id"], "input_summary": {"facts": len(state.get("discovered_facts", []))}}],
    }


def build_lead_graph() -> StateGraph:
    graph = StateGraph(LeadResearchState)
    graph.add_node("build_taxonomy", _build_taxonomy)
    graph.add_node("track_a", _track_a)
    graph.add_node("track_b", _track_b)
    graph.add_node("grade_evidence", _grade_evidence)
    graph.add_node("compact", _compact)
    graph.add_node("generate_gap", _generate_gap)
    graph.add_node("finalize", _finalize)

    graph.add_edge(START, "build_taxonomy")
    graph.add_edge("build_taxonomy", "track_a")
    graph.add_edge("track_a", "track_b")
    graph.add_edge("track_b", "grade_evidence")
    graph.add_edge("grade_evidence", "compact")
    graph.add_edge("compact", "generate_gap")
    graph.add_edge("generate_gap", "finalize")
    graph.add_edge("finalize", END)
    return graph


def compile_lead_graph(checkpointer=None):
    graph = build_lead_graph()
    if checkpointer is None:
        checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


async def run_lead_research(
    lead_id: str,
    business_id: str,
    lead: dict[str, Any],
    signal: dict[str, Any],
) -> dict:
    app = compile_lead_graph()
    initial = create_lead_state(
        lead_id=lead_id,
        business_id=business_id,
        lead=lead,
        signal=signal,
    )
    config = {"configurable": {"thread_id": f"research-{lead_id}"}, "recursion_limit": 50}
    final = await app.ainvoke(initial, config=config)
    return dict(final)