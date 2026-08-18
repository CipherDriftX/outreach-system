"""Track B — relationship walk for a lead.

The genuinely custom part. From the origin signal, walk one hop out:
who else is in the same thread, who replied, who shares the same topic.
Finds corroborating signals and connections a keyword search can't reach.
"""

from __future__ import annotations

from typing import Any

from src.llm.cascade import complete_tier


def walk_relationships(signal: dict, lead_facts: list[dict]) -> dict[str, Any]:
    prompt = f"""Analyze this origin signal and existing facts for relationship leads.

Origin signal:
- Source: {signal.get('source_name')} ({signal.get('source_type')})
- Author: {signal.get('author_handle') or 'unknown'}
- URL: {signal.get('url', '')}
- Text: {signal.get('raw_text', '')[:1000]}

Existing facts about this lead:
{chr(10).join(f'- [{f.get("fact_type")}] {f.get("fact", "")[:200]}' for f in lead_facts[:20])}

Task: identify relationship-based research directions:
1. Who else might be in the same conversation (co-commenters, thread participants)?
2. What second corroborating signal should we look for (a competitor complaining
   about the same thing, a shared connection)?
3. What entity-to-entity edges exist here (mentions, replies_to, works_with)?

Return ONLY valid JSON:
{{"edges": [{{"from_entity": "...", "to_entity": "...", "relation": "mentions|replies_to|works_with|co_comments", "weight": 0.0-1.0, "evidence": "..."}}],
  "research_directions": ["..."],
  "corroboration_notes": "..."}}"""

    import json

    result = complete_tier("mid", prompt)
    try:
        return json.loads(result.get("content", "{}"))
    except (json.JSONDecodeError, TypeError):
        return {"edges": [], "research_directions": [], "corroboration_notes": ""}


def persist_edges(
    business_id: str, edges: list[dict[str, Any]], source_url: str
) -> list[str]:
    from datetime import datetime, timezone
    from uuid import uuid4

    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    edge_ids: list[str] = []
    try:
        for edge in edges:
            eid = str(uuid4())
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO relationship_edges (id, business_id, from_entity,
                   to_entity, relation, weight, source_url, observed_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                [
                    eid,
                    business_id,
                    edge.get("from_entity", "")[:200],
                    edge.get("to_entity", "")[:200],
                    edge.get("relation", "mentions")[:50],
                    float(edge.get("weight", 0.5)),
                    source_url,
                    datetime.now(timezone.utc),
                ],
            )
            cur.close()
            edge_ids.append(eid)
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        put_connection(conn)
    return edge_ids