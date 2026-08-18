"""Settings API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.config import get_config
from src.db.queries import get_business_id

router = APIRouter(tags=["settings"])


class GovernorUpdate(BaseModel):
    path: str
    value: Any


@router.get("/settings")
def api_get_settings() -> dict:
    business_id = get_business_id()
    config = get_config()
    return {
        "business_id": business_id,
        "governors": config.governors,
    }


@router.put("/settings/governors")
def api_update_governor(body: GovernorUpdate) -> dict:
    import yaml
    from pathlib import Path

    config = get_config()
    governors = config.governors

    parts = body.path.split(".")
    target = governors
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = body.value

    path = Path(__file__).resolve().parents[3] / "config" / "governors.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(governors, f, default_flow_style=False, allow_unicode=True)

    config.governors = governors
    return {"status": "ok", "path": body.path, "value": body.value}