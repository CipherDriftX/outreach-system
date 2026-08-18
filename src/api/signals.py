"""Signals API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.db.queries import get_business_id, get_signals
from src.adapters.signals.registry import list_adapters

router = APIRouter(tags=["signals"])


@router.get("/signals")
def api_list_signals(limit: int = 100) -> list[dict]:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")
    return get_signals(business_id, limit=limit)


@router.get("/signals/adapters")
def api_list_adapters() -> list[dict]:
    return list_adapters()