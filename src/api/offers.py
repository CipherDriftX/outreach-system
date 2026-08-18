"""Offers API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.connection import get_connection, put_connection
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


@router.post("/offers/generate/{lead_id}")
def api_generate_offer(lead_id: str) -> dict:
    from src.nodes.offer.builder import generate_offer_for_lead

    result = generate_offer_for_lead(lead_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead, signal, or template not found")
    return result


@router.get("/offers")
def api_list_offers() -> list[dict]:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT o.id, o.lead_id, o.subject, o.unresolved_placeholders,
                      o.status, o.created_at,
                      l.company_name, l.contact_name, l.contact_email
               FROM offers o
               JOIN leads l ON o.lead_id = l.id
               WHERE l.business_id = %s
               ORDER BY o.created_at DESC LIMIT 100""",
            [business_id],
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "lead_id": r[1],
                "subject": r[2],
                "unresolved_placeholders": r[3],
                "status": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
                "company_name": r[6],
                "contact_name": r[7],
                "contact_email": r[8],
            }
            for r in rows
        ]
    finally:
        put_connection(conn)


@router.get("/offers/{offer_id}")
def api_get_offer(offer_id: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT o.id, o.lead_id, o.subject, o.body, o.resolved_fact_ids,
                      o.unresolved_placeholders, o.status, o.created_at,
                      l.company_name, l.contact_name
               FROM offers o
               JOIN leads l ON o.lead_id = l.id
               WHERE o.id = %s""",
            [offer_id],
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            raise HTTPException(status_code=404, detail="Offer not found")
        return {
            "id": row[0],
            "lead_id": row[1],
            "subject": row[2],
            "body": row[3],
            "resolved_fact_ids": row[4],
            "unresolved_placeholders": row[5],
            "status": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "company_name": row[8],
            "contact_name": row[9],
        }
    finally:
        put_connection(conn)


@router.get("/offers/template/placeholders")
def api_template_placeholders() -> dict:
    from src.nodes.offer.parser import extract_placeholders

    template = get_active_template(get_business_id() or "")
    if not template:
        return {"fact_placeholders": [], "signal_placeholders": [], "conditionals": []}
    return extract_placeholders(template["template_text"])


@router.post("/offers/generate-all")
def api_generate_all_offers() -> dict:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id FROM leads
               WHERE business_id = %s AND status = 'researched'
               LIMIT 50""",
            [business_id],
        )
        lead_ids = [r[0] for r in cur.fetchall()]
        cur.close()
    finally:
        put_connection(conn)

    from src.nodes.offer.builder import generate_offer_for_lead

    generated = 0
    for lead_id in lead_ids:
        try:
            result = generate_offer_for_lead(lead_id)
            if result:
                generated += 1
        except Exception:
            pass

    return {"generated": generated, "total": len(lead_ids)}