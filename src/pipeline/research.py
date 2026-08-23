"""Stage 2: Per-lead deep research.

For each signal scored >= 1, runs the full Node 2 LangGraph subgraph:
per-lead taxonomy -> enrichment Track A -> relationship Track B ->
evidence grading (four-axis) -> compaction dossier -> LLM gap hypothesis.

Pure in-memory. One subgraph instance per lead.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def _research_one(
    lead: dict[str, Any],
) -> dict[str, Any] | None:
    from src.nodes.research.graph import run_lead_research

    lead_id = lead.get("lead_id", "")
    signal = lead.get("signal", {})
    if not signal or not lead_id:
        return None

    lead_info = {
        "company_name": lead.get("company_name") or signal.get("author_handle", ""),
        "contact_name": lead.get("contact_name") or signal.get("author_handle", ""),
        "contact_email": None,
    }

    try:
        final = await run_lead_research(
            lead_id=lead_id,
            business_id="plarix",
            lead=lead_info,
            signal=signal,
        )
    except Exception as exc:
        logger.warning("research_failed", lead_id=lead_id, error=str(exc))
        return None

    facts = final.get("discovered_facts", [])
    gap = final.get("gap_hypothesis", {})
    lead_info = final.get("lead", lead_info)

    strong = sum(1 for f in facts if f.get("grade") == "strong")
    moderate = sum(1 for f in facts if f.get("grade") == "moderate")
    weak = sum(1 for f in facts if f.get("grade") == "weak")

    email = lead_info.get("contact_email")
    if email and "@" not in str(email):
        email = None

    return {
        "lead_id": lead_id,
        "signal_id": lead.get("signal_id", ""),
        "triage_score": lead.get("triage_score", 0),
        "company_name": lead_info.get("company_name"),
        "contact_name": lead_info.get("contact_name"),
        "contact_email": email,
        "gap_hypothesis": gap.get("hypothesis", ""),
        "facts": facts,
        "facts_strong": strong,
        "facts_moderate": moderate,
        "facts_weak": weak,
        "offer_subject": "",
        "offer_body": "",
        "unresolved": "",
    }


def research_signals(
    leads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []
    for lead in leads:
        try:
            result = asyncio.run(_research_one(lead))
            if result:
                results.append(result)
        except Exception as exc:
            logger.warning("research_failed", lead_id=lead.get("lead_id", "?"), error=str(exc))
    return results