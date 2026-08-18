"""Signal discovery core — the dual-track search engine for Node 1.

Runs Track A (intent queries) and Track B (lookalike walk) in parallel across
all active adapters for a given taxonomy vertical. Tracks frontier, novelty,
and per-adapter saturation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from src.adapters.signals.base import RawSignal
from src.adapters.signals.registry import all_adapters
from src.nodes.signal.queries import generate_intent_queries

logger = structlog.get_logger(__name__)


def discover_signals_for_vertical(
    vertical: dict[str, Any],
    previous_queries: list[str],
    successful_patterns: list[str],
    business_id: str,
    since: datetime | None = None,
) -> dict[str, Any]:
    queries = generate_intent_queries(vertical, previous_queries, successful_patterns)
    adapter_names = vertical.get("adapters", [])
    if not adapter_names:
        adapter_names = ["reddit", "hackernews", "twitter", "stackexchange", "github", "upwork", "bluesky"]

    all_raw: list[RawSignal] = []
    per_adapter_counts: dict[str, int] = {}

    for adapter in all_adapters():
        if adapter.name not in adapter_names:
            continue
        try:
            for query in queries:
                raw_signals = adapter.search(query, since)
                for s in raw_signals:
                    s["matched_pattern"] = query
                all_raw.extend(raw_signals)
                per_adapter_counts[adapter.name] = (
                    per_adapter_counts.get(adapter.name, 0) + len(raw_signals)
                )
        except Exception:
            logger.warning("adapter_search_failed", adapter=adapter.name, exc_info=True)

    # Frontier check: how many are actually new
    existing_urls = _get_existing_urls(business_id)
    new_signals = [s for s in all_raw if s["url"] not in existing_urls]

    # Dedup by URL within this batch
    seen: set[str] = set()
    deduped: list[RawSignal] = []
    for s in new_signals:
        if s["url"] not in seen:
            seen.add(s["url"])
            deduped.append(s)

    novelty = len(deduped) / max(len(all_raw), 1)

    return {
        "queries_issued": queries,
        "raw_total": len(all_raw),
        "new_count": len(deduped),
        "novelty": novelty,
        "signals": deduped,
        "per_adapter": per_adapter_counts,
    }


def _get_existing_urls(business_id: str) -> set[str]:
    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT url FROM signals WHERE business_id = %s", [business_id]
        )
        rows = cur.fetchall()
        cur.close()
        return {r[0] for r in rows}
    finally:
        put_connection(conn)


def persist_signals(
    business_id: str,
    signal_source_id: str,
    signals: list[RawSignal],
) -> list[str]:
    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    signal_ids: list[str] = []
    try:
        for s in signals:
            from uuid import uuid4

            sid = str(uuid4())
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO signals (id, business_id, signal_source_id,
                   source_type, source_name, url, author_handle, raw_text,
                   matched_pattern, posted_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                [
                    sid,
                    business_id,
                    signal_source_id,
                    s["source_type"],
                    s["source_name"],
                    s["url"],
                    s.get("author_handle"),
                    s["raw_text"],
                    s.get("matched_pattern", ""),
                    s.get("posted_at"),
                ],
            )
            cur.close()
            signal_ids.append(sid)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_connection(conn)

    return signal_ids