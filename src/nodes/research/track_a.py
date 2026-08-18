"""Track A — obvious facts about a lead.

Bought commodity: web-search enrichment for company/contact facts.
Everything found lands in lead_facts with track='A'.
"""

from __future__ import annotations

from typing import Any

from src.adapters.enrichment.web_search import WebSearchEnrichment


def research_obvious_facts(lead: dict, signal: dict) -> dict[str, Any]:
    enrichment = WebSearchEnrichment()
    result = enrichment.enrich(lead, signal)
    return {
        "track": "A",
        "facts": result.get("facts", []),
        "company_name": result.get("company_name"),
        "contact_name": result.get("contact_name"),
        "contact_email": result.get("contact_email"),
    }


def persist_facts(lead_id: str, facts: list[dict], track: str) -> list[str]:
    from uuid import uuid4

    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    fact_ids: list[str] = []
    try:
        for f in facts:
            fid = str(uuid4())
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO lead_facts (id, lead_id, fact_type, track, fact,
                   source_url, observed_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                [
                    fid,
                    lead_id,
                    f.get("fact_type", "observation"),
                    track,
                    f.get("fact", "")[:2000],
                    f.get("source_url"),
                    f.get("observed_at"),
                ],
            )
            cur.close()
            fact_ids.append(fid)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_connection(conn)
    return fact_ids