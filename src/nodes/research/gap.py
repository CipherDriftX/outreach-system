"""Gap hypothesis — the one fact that explains why this outreach exists.

A one-line, evidence-graded statement of what this specific lead needs,
tracing directly back to the origin signal. This is the fact the offer
leads with — not whichever fact happens to grade highest.
"""

from __future__ import annotations

import json
from typing import Any

from src.llm.cascade import complete_tier


def generate_gap_hypothesis(
    signal: dict, facts: list[dict[str, Any]]
) -> dict[str, Any]:
    fact_lines = "\n".join(
        f"- [{f.get('fact_type')}] ({f.get('grade', 'ungraded')}) {f.get('fact', '')[:250]}"
        for f in facts[:30]
    )

    prompt = f"""Formulate a gap hypothesis for this lead.

Origin signal (the ONLY reason we're reaching out):
- Source: {signal.get('source_name')} ({signal.get('source_type')})
- Author: {signal.get('author_handle') or 'unknown'}
- Text: {signal.get('raw_text', '')[:800]}

Facts discovered about this lead:
{fact_lines or '(no facts yet)'}

A gap hypothesis is a ONE-LINE statement: "This specific lead needs X because Y,
evidenced by Z." It must trace back to the origin signal — the hypothesis explains
the signal, not the other way around.

Rules:
- Must be grounded in the signal above AND at least one fact from the list.
- No invented numbers. No invented claims.
- If facts are insufficient, say so honestly.

Return ONLY valid JSON:
{{"hypothesis": "one line", "traces_to_signal": true, "supporting_fact_types": ["..."]}}"""

    result = complete_tier("frontier", prompt)
    try:
        data = json.loads(result.get("content", "{}"))
        hypothesis = data.get("hypothesis", "").strip()
        if not hypothesis:
            return {"hypothesis": "", "cost_usd": result.get("cost_usd", 0.0)}
        return {
            "hypothesis": hypothesis,
            "traces_to_signal": bool(data.get("traces_to_signal", True)),
            "supporting_fact_types": data.get("supporting_fact_types", []),
            "cost_usd": result.get("cost_usd", 0.0),
        }
    except Exception:
        return {"hypothesis": "", "cost_usd": result.get("cost_usd", 0.0)}


def persist_gap_hypothesis(lead_id: str, hypothesis: str) -> str | None:
    if not hypothesis:
        return None

    from uuid import uuid4

    from src.db.connection import get_connection, put_connection

    fid = str(uuid4())
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO lead_facts (id, lead_id, fact_type, track, fact)
               VALUES (%s, %s, 'gap_hypothesis', 'A', %s)""",
            [fid, lead_id, hypothesis[:1000]],
        )
        conn.commit()
        cur.close()
        return fid
    except Exception:
        conn.rollback()
        return None
    finally:
        put_connection(conn)