"""Node 2 — per-lead research subgraph.

One instance per lead that cleared triage, fanned out via LangGraph's Send API.
Runs: track_a → track_b → evidence grading → compaction → gap hypothesis.

Each lead fails alone — a bad lead never blocks the others.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

import structlog
from langgraph.graph import END, START, StateGraph

logger = structlog.get_logger(__name__)


def _merge_unique_append(existing: list[str], new: list[str]) -> list[str]:
    seen = set(existing)
    return existing + [item for item in new if item not in seen and not seen.add(item)]


def _merge_errors(existing: list[dict], new: list[dict]) -> list[dict]:
    return (existing or []) + (new or [])


def _accumulate_float(a: float, b: float) -> float:
    return (a or 0.0) + (b or 0.0)


class LeadResearchState(TypedDict, total=False):
    lead_id: str
    business_id: str
    origin_signal_id: str

    lead: dict[str, Any]
    signal: dict[str, Any]

    taxonomy: dict[str, Any]
    track_a_done: bool
    track_b_done: bool

    discovered_fact_ids: Annotated[list[str], _merge_unique_append]

    dossier: dict[str, Any] | None
    gap_hypothesis: dict[str, Any] | None

    budget_spent_usd: Annotated[float, _accumulate_float]
    errors: Annotated[list[dict], _merge_errors]
    node_logs: Annotated[list[dict], _merge_errors]

    schema_version: int


def _load_lead(state: LeadResearchState) -> dict:
    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    lead_data = None
    signal_data = None
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, company_name, contact_name, contact_email, origin_signal_id
               FROM leads WHERE id = %s""",
            [state["lead_id"]],
        )
        row = cur.fetchone()
        if row:
            lead_data = {
                "id": row[0],
                "company_name": row[1],
                "contact_name": row[2],
                "contact_email": row[3],
            }
            cur.execute(
                """SELECT id, source_name, source_type, url, author_handle, raw_text
                   FROM signals WHERE id = %s""",
                [row[4]],
            )
            srow = cur.fetchone()
            if srow:
                signal_data = {
                    "id": srow[0],
                    "source_name": srow[1],
                    "source_type": srow[2],
                    "url": srow[3],
                    "author_handle": srow[4],
                    "raw_text": srow[5],
                }
        cur.close()
    finally:
        put_connection(conn)

    if not lead_data or not signal_data:
        return {"errors": [{"node_name": "load_lead", "message": "lead or signal not found", "recoverable": False}]}

    conn2 = get_connection()
    try:
        cur = conn2.cursor()
        cur.execute("UPDATE leads SET status = 'researching' WHERE id = %s", [state["lead_id"]])
        conn2.commit()
        cur.close()
    finally:
        put_connection(conn2)

    return {
        "lead": lead_data,
        "signal": signal_data,
        "node_logs": [
            {"node_name": "load_lead", "thread_id": "", "input_summary": {"lead": lead_data.get("company_name") or lead_data.get("contact_name") or "unknown"}}
        ],
    }


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
    from src.db.connection import get_connection, put_connection
    from src.nodes.research.track_a import persist_facts, research_obvious_facts

    lead = state.get("lead", {})
    signal = state.get("signal", {})
    result = research_obvious_facts(lead, signal)
    fact_ids = persist_facts(state["lead_id"], result.get("facts", []), "A")

    # Backfill lead row with enrichment-discovered identity, never overwriting
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE leads
               SET company_name = COALESCE(company_name, %s),
                   contact_name = COALESCE(contact_name, %s),
                   contact_email = COALESCE(contact_email, %s)
               WHERE id = %s""",
            [
                result.get("company_name"),
                result.get("contact_name"),
                result.get("contact_email"),
                state["lead_id"],
            ],
        )
        conn.commit()
        cur.close()
    finally:
        put_connection(conn)

    return {
        "discovered_fact_ids": fact_ids,
        "track_a_done": True,
        "node_logs": [
            {"node_name": "track_a", "thread_id": "", "input_summary": {"facts": len(fact_ids)}}
        ],
    }


def _track_b(state: LeadResearchState) -> dict:
    from src.db.queries import get_lead_facts
    from src.nodes.research.track_b import persist_edges, walk_relationships

    signal = state.get("signal", {})
    facts = get_lead_facts(state["lead_id"])
    result = walk_relationships(signal, facts)
    edge_ids = persist_edges(
        state.get("business_id", ""), result.get("edges", []), signal.get("url", "")
    )

    extra_facts = []
    for direction in result.get("research_directions", [])[:3]:
        if direction:
            extra_facts.append(
                {
                    "fact": f"Research direction: {direction}",
                    "fact_type": "relationship_context",
                    "source_url": signal.get("url"),
                }
            )
    fact_ids = []
    if extra_facts:
        from src.nodes.research.track_a import persist_facts as pf

        fact_ids = pf(state["lead_id"], extra_facts, "B")

    return {
        "discovered_fact_ids": fact_ids,
        "track_b_done": True,
        "node_logs": [
            {"node_name": "track_b", "lead_id": state["lead_id"], "input_summary": {"edges": len(edge_ids), "facts": len(fact_ids)}}
        ],
    }


def _grade_evidence(state: LeadResearchState) -> dict:
    from src.nodes.research.evidence import update_fact_grades

    graded = update_fact_grades(state["lead_id"])
    strong = sum(1 for f in graded if f.get("grade") == "strong")
    moderate = sum(1 for f in graded if f.get("grade") == "moderate")
    weak = sum(1 for f in graded if f.get("grade") == "weak")
    return {
        "node_logs": [
            {"node_name": "grade_evidence", "lead_id": state["lead_id"], "input_summary": {"strong": strong, "moderate": moderate, "weak": weak}}
        ],
    }


def _compact(state: LeadResearchState) -> dict:
    from src.db.queries import get_lead_facts
    from src.nodes.research.compaction import compact_lead

    lead = state.get("lead", {})
    facts = get_lead_facts(state["lead_id"])
    dossier = compact_lead(lead, facts)
    return {
        "dossier": dossier,
        "budget_spent_usd": dossier.get("cost_usd", 0.0),
    }


def _generate_gap(state: LeadResearchState) -> dict:
    from src.db.queries import get_lead_facts
    from src.nodes.research.gap import generate_gap_hypothesis, persist_gap_hypothesis

    signal = state.get("signal", {})
    facts = get_lead_facts(state["lead_id"])
    result = generate_gap_hypothesis(signal, facts)
    gap_id = persist_gap_hypothesis(state["lead_id"], result.get("hypothesis", ""))
    return {
        "gap_hypothesis": {
            "fact_id": gap_id,
            "hypothesis": result.get("hypothesis", ""),
            "traces_to_signal": result.get("traces_to_signal", True),
        },
        "budget_spent_usd": result.get("cost_usd", 0.0),
        "node_logs": [
            {"node_name": "generate_gap", "lead_id": state["lead_id"], "input_summary": {"hypothesis": (result.get("hypothesis") or "")[:80]}}
        ],
    }


def _finalize(state: LeadResearchState) -> dict:
    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE leads SET status = 'researched' WHERE id = %s",
            [state["lead_id"]],
        )
        conn.commit()
        cur.close()
    finally:
        put_connection(conn)

    return {
        "node_logs": [
            {"node_name": "finalize", "lead_id": state["lead_id"], "input_summary": {"status": "researched"}}
        ],
    }


def build_lead_graph() -> StateGraph:
    graph = StateGraph(LeadResearchState)

    graph.add_node("load_lead", _load_lead)
    graph.add_node("build_taxonomy", _build_taxonomy)
    graph.add_node("track_a", _track_a)
    graph.add_node("track_b", _track_b)
    graph.add_node("grade_evidence", _grade_evidence)
    graph.add_node("compact", _compact)
    graph.add_node("generate_gap", _generate_gap)
    graph.add_node("finalize", _finalize)

    graph.add_edge(START, "load_lead")
    graph.add_edge("load_lead", "build_taxonomy")
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
    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()