"""Signals API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.db.queries import get_business_id, get_signals

router = APIRouter(tags=["signals"])


@router.get("/signals")
def api_list_signals(limit: int = 100) -> list[dict]:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")
    return get_signals(business_id, limit=limit)