"""graph.py — LangGraph wiring for Node 1 (Signal Discovery).

Flow:
START → init_run → select_next_vertical → discover_vertical
    → triage_signals → check_saturation
    → route: expand_deeper | detect_splits | done → END
"""

from __future__ import annotations

import structlog

from langgraph.graph import END, START, StateGraph

from src.state import SignalGraphState, create_initial_state, migrate_state

logger = structlog.get_logger(__name__)


def _init_run(state: SignalGraphState) -> dict:
    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])
    return {
        "node_logs": [
            {
                "node_name": "init_run",
                "thread_id": state.get("thread_id", ""),
                "input_summary": {
                    "vertical_count": len(verticals),
                    "root": (taxonomy.get("root") or "")[:80],
                },
            }
        ],
    }


def _select_next_vertical(state: SignalGraphState) -> dict:
    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])
    expanded = state.get("expanded_vertical_labels", set())

    next_vertical = None
    for v in verticals:
        if v.get("label") not in expanded:
            next_vertical = v
            break

    if next_vertical is None:
        return {"current_phase": "done"}

    return {
        "expanded_vertical_labels": {next_vertical["label"]},
        "active_vertical_index": verticals.index(next_vertical),
    }


def _discover_vertical(state: SignalGraphState) -> dict:
    from src.db.connection import get_connection, put_connection
    from src.nodes.signal.discovery import discover_signals_for_vertical, persist_signals

    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])
    idx = state.get("active_vertical_index", 0)
    if idx >= len(verticals):
        return {"current_phase": "done"}

    vertical = verticals[idx]
    label = vertical.get("label", "unknown")
    previous_queries = state.get("queries_by_vertical", {}).get(label, [])
    successful_patterns = state.get("successful_patterns", [])

    business_id = state["business_id"]

    # Ensure signal_sources row exists for this adapter run
    conn = get_connection()
    signal_source_id = None
    try:
        cur = conn.cursor()
        from uuid import uuid4
        cur.execute(
            """INSERT INTO signal_sources (id, business_id, adapter, track, config)
               VALUES (%s, %s, 'multi', 'A', '{}'::jsonb)
               ON CONFLICT DO NOTHING""",
            [str(uuid4()), business_id],
        )
        conn.commit()
        cur.execute(
            """SELECT id FROM signal_sources WHERE business_id = %s AND adapter = 'multi'
               ORDER BY created_at DESC LIMIT 1""",
            [business_id],
        )
        row = cur.fetchone()
        if row:
            signal_source_id = row[0]
        cur.close()
    except Exception:
        conn.rollback()
    finally:
        put_connection(conn)

    result = discover_signals_for_vertical(
        vertical=vertical,
        previous_queries=previous_queries,
        successful_patterns=successful_patterns,
        business_id=business_id,
    )

    new_signal_ids: list[str] = []
    if result["signals"]:
        new_signal_ids = persist_signals(
            business_id, signal_source_id or "", result["signals"]
        )

    # Track novelty per adapter
    novelty_updates: dict[str, list[float]] = {}
    for adapter_name, count in result["per_adapter"].items():
        total = count
        if total > 0:
            new = sum(1 for s in result["signals"] if s["source_name"] == adapter_name)
            novelty_updates[adapter_name] = [new / total]

    queries_by_vertical = dict(state.get("queries_by_vertical", {}))
    queries_by_vertical[label] = previous_queries + result["queries_issued"]

    return {
        "discovered_signal_ids": new_signal_ids,
        "queries_by_vertical": queries_by_vertical,
        "novelty_history": novelty_updates,
        "successful_patterns": successful_patterns + [
            q for q in result["queries_issued"] if result["new_count"] > 0
        ],
        "node_logs": [
            {
                "node_name": "discover_vertical",
                "thread_id": state.get("thread_id", ""),
                "input_summary": {
                    "vertical": label,
                    "queries": len(result["queries_issued"]),
                    "raw": result["raw_total"],
                    "new": result["new_count"],
                    "novelty": round(result["novelty"], 3),
                },
            }
        ],
    }


def _triage_signals(state: SignalGraphState) -> dict:
    from src.db.connection import get_connection, put_connection
    from src.nodes.signal.triage import triage_signal, create_lead_from_signal

    new_signal_ids = state.get("discovered_signal_ids", [])
    if not new_signal_ids:
        return {}

    triaged = state.get("triaged_signal_ids", set())
    pending = [sid for sid in new_signal_ids if sid not in triaged]
    if not pending:
        return {}

    taxonomy = state.get("taxonomy", {})
    icp_root = taxonomy.get("root", "")

    conn = get_connection()
    signals = []
    try:
        cur = conn.cursor()
        for sid in pending[-200:]:  # bounded batch
            cur.execute(
                """SELECT id, source_name, source_type, url, author_handle, raw_text
                   FROM signals WHERE id = %s""",
                [sid],
            )
            row = cur.fetchone()
            if row:
                signals.append(
                    {
                        "id": row[0],
                        "source_name": row[1],
                        "source_type": row[2],
                        "url": row[3],
                        "author_handle": row[4],
                        "raw_text": row[5],
                    }
                )
        cur.close()
    finally:
        put_connection(conn)

    new_lead_ids: list[str] = []
    triaged_this_round: set[str] = set()
    for signal in signals[:50]:  # bounded LLM calls per round
        result = triage_signal(signal, icp_root)
        triaged_this_round.add(signal["id"])
        lead_id = create_lead_from_signal(state["business_id"], signal, result)
        if lead_id:
            new_lead_ids.append(lead_id)

    return {
        "discovered_lead_ids": new_lead_ids,
        "triaged_signal_ids": triaged_this_round,
        "node_logs": [
            {
                "node_name": "triage_signals",
                "thread_id": state.get("thread_id", ""),
                "input_summary": {
                    "triaged": len(signals),
                    "leads_created": len(new_lead_ids),
                },
            }
        ],
    }


def _check_saturation(state: SignalGraphState) -> dict:
    from src.nodes.signal.saturation import check_adapter_saturation

    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])
    expanded = state.get("expanded_vertical_labels", set())
    novelty_history = state.get("novelty_history", {})

    statuses = []
    for adapter_name, history in novelty_history.items():
        statuses.append(check_adapter_saturation(adapter_name, history))

    remaining = [v for v in verticals if v.get("label") not in expanded]
    if remaining:
        return {"current_phase": "discovering"}

    # All verticals expanded. Check if the taxonomy should split.
    saturated_adapters = [s for s in statuses if s["saturated"]]
    if saturated_adapters:
        return {"current_phase": "splitting"}

    return {"current_phase": "done"}


def _detect_splits(state: SignalGraphState) -> dict:
    from src.db.connection import get_connection, put_connection
    from src.nodes.signal.split import detect_splits

    business_id = state["business_id"]
    taxonomy = state.get("taxonomy", {})
    verticals = taxonomy.get("verticals", [])

    conn = get_connection()
    all_signals = []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT raw_text, matched_pattern FROM signals WHERE business_id = %s LIMIT 500",
            [business_id],
        )
        all_signals = [
            {"raw_text": r[0], "matched_pattern": r[1]} for r in cur.fetchall()
        ]
        cur.close()
    finally:
        put_connection(conn)

    new_verticals = []
    for vertical in verticals:
        vertical_signals = [
            s for s in all_signals if s.get("matched_pattern", "") in vertical.get("intent_patterns", [])
        ]
        new_verticals.extend(detect_splits(vertical, vertical_signals))

    if new_verticals:
        updated = dict(taxonomy)
        updated["verticals"] = verticals + new_verticals
        return {
            "taxonomy": updated,
            "current_phase": "discovering",
            "node_logs": [
                {
                    "node_name": "detect_splits",
                    "thread_id": state.get("thread_id", ""),
                    "input_summary": {"new_verticals": len(new_verticals)},
                }
            ],
        }

    return {"current_phase": "done"}


def route_after_saturation(state: SignalGraphState) -> list[str]:
    phase = state.get("current_phase", "discovering")
    if phase == "discovering":
        return ["select_next_vertical"]
    if phase == "splitting":
        return ["detect_splits"]
    return [END]


def route_after_splits(state: SignalGraphState) -> list[str]:
    phase = state.get("current_phase", "done")
    if phase == "discovering":
        return ["select_next_vertical"]
    return [END]


def build_graph() -> StateGraph:
    graph = StateGraph(SignalGraphState)

    graph.add_node("init_run", _init_run)
    graph.add_node("select_next_vertical", _select_next_vertical)
    graph.add_node("discover_vertical", _discover_vertical)
    graph.add_node("triage_signals", _triage_signals)
    graph.add_node("check_saturation", _check_saturation)
    graph.add_node("detect_splits", _detect_splits)

    graph.add_edge(START, "init_run")
    graph.add_edge("init_run", "select_next_vertical")
    graph.add_edge("select_next_vertical", "discover_vertical")
    graph.add_edge("discover_vertical", "triage_signals")
    graph.add_edge("triage_signals", "check_saturation")
    graph.add_conditional_edges(
        "check_saturation",
        route_after_saturation,
        ["select_next_vertical", "detect_splits", END],
    )
    graph.add_conditional_edges(
        "detect_splits",
        route_after_splits,
        ["select_next_vertical", END],
    )

    return graph


def compile_graph(checkpointer=None):
    graph = build_graph()
    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


async def run_signal_discovery(
    business_id: str,
    run_id: str,
    thread_id: str,
    taxonomy: dict,
    checkpointer=None,
) -> dict:
    from src.config import get_config

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 200,
    }
    app = compile_graph(checkpointer=checkpointer)
    initial = create_initial_state(
        business_id=business_id,
        run_id=run_id,
        thread_id=thread_id,
        taxonomy=taxonomy,
        budget_limit_usd=get_config().governors.get("research", {}).get("budget_limit_usd_per_run", 5.0),
    )
    final = await app.ainvoke(initial, config=config)
    return migrate_state(final)