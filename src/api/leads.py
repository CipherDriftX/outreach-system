"""Leads API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.db.queries import (
    get_business_id,
    get_gap_hypothesis,
    get_lead_facts,
    get_leads_by_status,
)

router = APIRouter(tags=["leads"])


@router.get("/leads")
def api_list_leads(status: str | None = None) -> list[dict]:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")
    s = status or "found"
    return get_leads_by_status(s)


@router.get("/leads/{lead_id}")
def api_get_lead(lead_id: str) -> dict:
    facts = get_lead_facts(lead_id)
    gap = get_gap_hypothesis(lead_id)
    return {
        "lead_id": lead_id,
        "facts": facts,
        "gap_hypothesis": gap,
        "fact_count": len(facts),
        "strong_count": sum(1 for f in facts if f.get("grade") == "strong"),
        "moderate_count": sum(1 for f in facts if f.get("grade") == "moderate"),
        "weak_count": sum(1 for f in facts if f.get("grade") == "weak"),
    }


@router.get("/leads/{lead_id}/facts")
def api_lead_facts(lead_id: str) -> list[dict]:
    return get_lead_facts(lead_id)


@router.get("/leads/{lead_id}/gap")
def api_lead_gap(lead_id: str) -> dict | None:
    return get_gap_hypothesis(lead_id)