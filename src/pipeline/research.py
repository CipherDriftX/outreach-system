"""Stage 2: Per-Lead Research Pipeline.

For each triaged signal (score >= 1), runs dual-track research:
  Track A: web-search enrichment + LLM fact extraction
  Track B: relationship walk
Then: evidence grading, compaction, gap hypothesis.
Returns lead dicts ready for Excel. No database.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from src.adapters.enrichment.web_search import WebSearchEnrichment
from src.llm.cascade import complete_tier
from src.nodes.research.evidence import grade_fact
from src.nodes.research.track_b import walk_relationships

logger = structlog.get_logger(__name__)


def research_signals(
    signals: list[dict[str, Any]],
    icp_root: str = "",
) -> list[dict[str, Any]]:
    enrichment = WebSearchEnrichment()
    leads: list[dict[str, Any]] = []

    qualified = [s for s in signals if s.get("triage_score", 0) >= 1]
    if not qualified:
        return leads

    for signal in qualified:
        try:
            lead = _research_one(signal, enrichment, icp_root)
            if lead:
                leads.append(lead)
        except Exception as exc:
            logger.warning("research_failed", signal_id=signal.get("signal_id"), error=str(exc))

    return leads


def _research_one(
    signal: dict[str, Any],
    enrichment: WebSearchEnrichment,
    icp_root: str,
) -> dict[str, Any] | None:
    lead_id = str(uuid.uuid4())
    author = signal.get("author_handle") or ""

    # Track A: enrichment
    lead_stub = {"company_name": author, "contact_name": author, "contact_email": None}
    enrich_result = enrichment.enrich(lead_stub, signal)
    facts = enrich_result.get("facts", [])

    # Extract company name from facts
    company_name = enrich_result.get("company_name") or author
    contact_name = enrich_result.get("contact_name") or author

    # Add enriched facts with Track A attribution
    track_a_facts = []
    for f in facts:
        fid = str(uuid.uuid4())
        track_a_facts.append({
            "id": fid,
            "fact_type": f.get("fact_type", "observation"),
            "track": "A",
            "fact": f.get("fact", "")[:2000],
            "source_url": f.get("source_url"),
            "observed_at": f.get("observed_at"),
            "corroboration_count": 1,
            "recency_days": None,
        })

    # Track B: relationship walk
    track_b_result = walk_relationships(signal, track_a_facts)
    for direction in track_b_result.get("research_directions", [])[:3]:
        if direction:
            fid = str(uuid.uuid4())
            track_a_facts.append({
                "id": fid,
                "fact_type": "relationship_context",
                "track": "B",
                "fact": direction,
                "source_url": signal.get("url"),
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "corroboration_count": 1,
                "recency_days": None,
            })

    # Evidence grade every fact
    all_facts = track_a_facts
    for f in all_facts:
        grade = grade_fact(f)
        f["grade"] = grade["grade"]
        f["axis_scores"] = grade["axis_scores"]

    strong = sum(1 for f in all_facts if f.get("grade") == "strong")
    moderate = sum(1 for f in all_facts if f.get("grade") == "moderate")
    weak = sum(1 for f in all_facts if f.get("grade") == "weak")

    # Gap hypothesis
    try:
        gap = _generate_gap(signal, all_facts)
    except Exception:
        gap = _keyword_gap(signal)

    return {
        "lead_id": lead_id,
        "signal_id": signal.get("signal_id", ""),
        "triage_score": signal.get("triage_score", 0),
        "company_name": company_name,
        "contact_name": contact_name,
        "contact_email": enrich_result.get("contact_email"),
        "gap_hypothesis": gap,
        "facts": all_facts,
        "facts_strong": strong,
        "facts_moderate": moderate,
        "facts_weak": weak,
        "offer_subject": "",
        "offer_body": "",
        "unresolved": "",
    }


def _generate_gap(signal: dict, facts: list[dict]) -> str:
    fact_lines = "\n".join(
        f"- [{f.get('fact_type')}] ({f.get('grade', 'ungraded')}) {f.get('fact', '')[:200]}"
        for f in facts[:20]
    )
    prompt = f"""Formulate a gap hypothesis for this lead.

Origin signal:
Source: {signal.get('source_name')} ({signal.get('source_type')})
Text: {signal.get('raw_text', '')[:800]}

Facts:
{fact_lines or '(no facts)'}

A gap hypothesis is ONE SENTENCE: "This [person/company] needs X because Y, evidenced by Z."
Must be grounded in the signal above. Return ONLY the sentence, no preamble."""

    result = complete_tier("mid", prompt)
    hypothesis = result.get("content", "").strip()
    if hypothesis.startswith('"') and hypothesis.endswith('"'):
        hypothesis = hypothesis[1:-1]
    return hypothesis[:300]


def _keyword_gap(signal: dict) -> str:
    text = signal.get("raw_text", "")
    source = signal.get("source_name", "")
    author = signal.get("author_handle", "this person")
    return f"{author} on {source} is expressing a need related to operational process automation, evidenced by their post about {text[:120]}"