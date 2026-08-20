"""Stage 3: Offer Crafting Pipeline.

Reads the offer template from config/template.txt and fills it for each
researched lead using the deterministic template engine. Grade-gated:
weak facts can't back claims; missing facts are omitted, not invented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.nodes.offer.builder import build_offer


TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "config" / "template.txt"


def load_template() -> str:
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    return ""


def craft_offers(
    leads: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    grade_floor: str = "moderate",
) -> list[dict[str, Any]]:
    template = load_template()
    if not template:
        return leads

    signal_map: dict[str, dict[str, Any]] = {}
    for s in signals:
        sid = s.get("signal_id", "")
        if sid:
            signal_map[sid] = s

    for lead in leads:
        sid = lead.get("signal_id", "")
        signal = signal_map.get(sid, {})

        if not signal:
            lead["offer_subject"] = ""
            lead["offer_body"] = ""
            lead["unresolved"] = "missing signal"
            continue

        lead_info = {
            "company_name": lead.get("company_name"),
            "contact_name": lead.get("contact_name"),
            "contact_email": lead.get("contact_email"),
        }
        facts = lead.get("facts", [])

        try:
            result = build_offer(template, lead_info, signal, facts, grade_floor=grade_floor)
            lead["offer_subject"] = result.get("subject", "")
            lead["offer_body"] = result.get("body", "")
            unresolved = result.get("unresolved_placeholders", [])
            lead["unresolved"] = ", ".join(unresolved) if unresolved else ""
        except Exception:
            lead["offer_subject"] = ""
            lead["offer_body"] = ""
            lead["unresolved"] = "build error"

    return leads