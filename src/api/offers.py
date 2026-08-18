"""Offers API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.queries import (
    get_active_template,
    get_business_id,
    upsert_template,
)

router = APIRouter(tags=["offers"])


class TemplateUpdate(BaseModel):
    template_text: str


@router.get("/offers/template")
def api_get_template() -> dict:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")
    template = get_active_template(business_id)
    if not template:
        from src.config import get_config
        default = get_config().governors.get("craft", {}).get("default_template", "")
        return {"template_text": default, "id": None, "name": "default"}
    return template


@router.put("/offers/template")
def api_update_template(body: TemplateUpdate) -> dict:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")
    return upsert_template(business_id, body.template_text)