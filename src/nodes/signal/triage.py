"""Triage gate for signals → leads.

Scores each signal 0-3 on relevance. Only signals scoring >= 1 create leads.
0 = noise, 1 = potential, 2 = relevant, 3 = high-confidence match.
"""

from __future__ import annotations

import json
from typing import Any

from src.llm.cascade import complete_tier


def triage_signal(
    signal: dict[str, Any],
    icp_root: str,
) -> dict[str, Any]:
    prompt = f"""Score this signal on relevance to our business.

Our ICP: "{icp_root}"

Signal:
Source: {signal.get('source_name')} ({signal.get('source_type')})
Text: {signal.get('raw_text', '')[:500]}

Score 0-3:
0 = Not relevant at all (noise, unrelated topic)
1 = Potentially relevant (vague, could be relevant but unclear)
2 = Relevant (clearly expresses a need we could address)
3 = High-confidence (exact match, strong buying signal, urgency)

Return ONLY valid JSON: {{"score": 0-3, "reasoning": "one sentence why"}}"""

    result = complete_tier("cheap", prompt)
    try:
        data = json.loads(result.get("content", "{}"))
        score = int(data.get("score", 0))
        return {
            "score": max(0, min(3, score)),
            "reasoning": data.get("reasoning", ""),
            "cost_usd": result.get("cost_usd", 0.0),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"score": 0, "reasoning": "parse error", "cost_usd": result.get("cost_usd", 0.0)}


def create_lead_from_signal(
    business_id: str,
    signal: dict[str, Any],
    triage_result: dict[str, Any],
) -> str | None:
    if triage_result.get("score", 0) < 1:
        return None

    import hashlib
    from uuid import uuid4
    from src.db.connection import get_connection, put_connection

    lead_id = str(uuid4())
    dedup_key = f"{signal.get('source_name')}:{hashlib.md5(signal.get('url', '').encode()).hexdigest()[:12]}"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO leads (id, business_id, origin_signal_id, signal_strength_score, dedup_key, status)
               VALUES (%s, %s, %s, %s, %s, 'found')
               ON CONFLICT (dedup_key) DO NOTHING""",
            [lead_id, business_id, signal["id"], triage_result["score"], dedup_key],
        )
        conn.commit()
        cur.close()
        return lead_id
    except Exception:
        conn.rollback()
        return None
    finally:
        put_connection(conn)