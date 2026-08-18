"""Dashboard API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from src.db.queries import get_business_id, get_pipeline_stats

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def api_dashboard() -> dict:
    business_id = get_business_id()
    if not business_id:
        return {"error": "No business configured"}
    stats = get_pipeline_stats(business_id)
    return {
        "pipeline": stats,
        "business_id": business_id,
    }