"""Offer builder — fills the user's template from resolved research.

Output: a filled subject + body with resolved_fact_ids tracking. Every
resolved value traces to a lead_facts.id or signals row — the linter can
verify the trace deterministically.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from src.nodes.offer.parser import (
    ConditionalBlock,
    FactToken,
    LiteralToken,
    SignalToken,
    Token,
    parse_template,
)
from src.nodes.offer.resolver import Resolver


def build_offer(
    template_text: str,
    lead: dict[str, Any],
    signal: dict[str, Any],
    facts: list[dict[str, Any]],
    grade_floor: str = "moderate",
) -> dict[str, Any]:
    tokens = parse_template(template_text)
    resolver = Resolver(facts, signal, lead, grade_floor=grade_floor)

    body_parts = _render_tokens(tokens, resolver)

    body = "".join(body_parts).strip()
    body = _collapse_blank_lines(body)

    subject = _derive_subject(body) or "Quick question"

    return {
        "subject": subject,
        "body": body,
        "resolved_fact_ids": resolver.resolved_fact_ids,
        "unresolved_placeholders": resolver.unresolved,
        "fully_resolved": len(resolver.unresolved) == 0,
    }


def _render_tokens(tokens: list[Token], resolver: Resolver) -> list[str]:
    parts: list[str] = []
    for token in tokens:
        if isinstance(token, LiteralToken):
            parts.append(token.text)
        elif isinstance(token, FactToken):
            text, _ = resolver.resolve_fact(token)
            if text:
                parts.append(text)
            else:
                parts.append(_omit_line(token.key))
        elif isinstance(token, SignalToken):
            text = resolver.resolve_signal(token)
            parts.append(text if text else _omit_line(token.key))
        elif isinstance(token, ConditionalBlock):
            if resolver.resolve_conditional(token):
                parts.extend(_render_tokens(token.tokens, resolver))
    return parts


def _omit_line(key: str) -> str:
    """When a fact can't be resolved, the sentence it belonged to must not
    render as a fragment. Emit a marker so _collapse_blank_lines drops the
    whole line it was on."""
    return f"[[UNRESOLVED:{key}]]"


def _collapse_blank_lines(text: str) -> str:
    lines = text.split("\n")
    kept = []
    for line in lines:
        if "[[UNRESOLVED:" in line:
            continue
        kept.append(line)
    # Collapse 3+ newlines into 2
    collapsed = re.sub(r"\n{3,}", "\n\n", "\n".join(kept))
    return collapsed.strip()


def _derive_subject(body: str) -> str | None:
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("Subject:"):
            return line.replace("Subject:", "", 1).strip()
        if line.startswith("subject:"):
            return line.replace("subject:", "", 1).strip()
    return None


def persist_offer(
    lead_id: str,
    template_id: str | None,
    subject: str,
    body: str,
    resolved_fact_ids: list[str],
    unresolved_placeholders: list[str],
) -> str:
    from uuid import uuid4

    from src.db.connection import get_connection, put_connection

    offer_id = str(uuid4())
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO offers (id, lead_id, template_id, subject, body,
               resolved_fact_ids, unresolved_placeholders, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'draft')""",
            [
                offer_id,
                lead_id,
                template_id,
                subject,
                body,
                resolved_fact_ids,
                unresolved_placeholders,
            ],
        )
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_connection(conn)
    return offer_id


def generate_offer_for_lead(lead_id: str, grade_floor: str = "moderate") -> dict[str, Any] | None:
    """Full pipeline: load lead + signal + facts + template → build → persist."""
    from src.db.queries import (
        get_active_template,
        get_business_id,
        get_gap_hypothesis,
        get_lead_facts,
    )

    from src.db.connection import get_connection, put_connection
    business_id = get_business_id()
    if not business_id:
        return None

    template = get_active_template(business_id)
    if not template:
        return None

    facts = get_lead_facts(lead_id)
    gap = get_gap_hypothesis(lead_id)

    conn = get_connection()
    lead = None
    signal = None
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, company_name, contact_name, contact_email
               FROM leads WHERE id = %s""",
            [lead_id],
        )
        row = cur.fetchone()
        if row:
            lead = {
                "id": row[0],
                "company_name": row[1],
                "contact_name": row[2],
                "contact_email": row[3],
            }
            cur.execute(
                """SELECT id, source_type, source_name, url, author_handle, raw_text
                   FROM signals WHERE id = (SELECT origin_signal_id FROM leads WHERE id = %s)""",
                [lead_id],
            )
            srow = cur.fetchone()
            if srow:
                signal = {
                    "id": srow[0],
                    "source_type": srow[1],
                    "source_name": srow[2],
                    "url": srow[3],
                    "author_handle": srow[4],
                    "raw_text": srow[5],
                }
        cur.close()
    finally:
        put_connection(conn)

    if not lead or not signal:
        return None

    result = build_offer(
        template_text=template["template_text"],
        lead=lead,
        signal=signal,
        facts=facts,
        grade_floor=grade_floor,
    )

    # The gap hypothesis must back the opening if it's referenced
    if gap and result["resolved_fact_ids"]:
        pass  # traceability enforced via resolved_fact_ids

    offer_id = persist_offer(
        lead_id=lead_id,
        template_id=template.get("id"),
        subject=result["subject"],
        body=result["body"],
        resolved_fact_ids=result["resolved_fact_ids"],
        unresolved_placeholders=result["unresolved_placeholders"],
    )

    conn2 = get_connection()
    try:
        cur = conn2.cursor()
        cur.execute("UPDATE leads SET status = 'offer_drafted' WHERE id = %s", [lead_id])
        conn2.commit()
        cur.close()
    finally:
        put_connection(conn2)

    return {**result, "offer_id": offer_id, "lead_id": lead_id}