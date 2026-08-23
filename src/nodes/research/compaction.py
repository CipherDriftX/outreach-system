"""Compaction — raw facts → narrative dossier.

Two hard rules:
1. Numbers never move through narrative. The LLM narrates facts that are
   ALREADY in lead_facts rows. It is forbidden from inventing any.
2. The dossier is a summary; every claim in it must trace to a lead_facts row.
"""

from __future__ import annotations

import json
from typing import Any

from src.llm.cascade import complete_tier


def compact_lead(lead: dict, facts: list[dict[str, Any]]) -> dict[str, Any]:
    if not facts:
        return {"summary": "", "key_points": [], "cost_usd": 0.0}

    fact_lines = "\n".join(
        f"{i+1}. [{f.get('fact_type')}] ({f.get('grade', 'ungraded')}) {f.get('fact', '')[:300]}"
        for i, f in enumerate(facts[:40])
    )

    prompt = f"""Summarize these facts about a lead into a compact dossier.

Lead: {lead.get('company_name') or 'unknown'} — contact {lead.get('contact_name') or 'unknown'}

Facts (each fact is numbered and carries its evidence grade):
{fact_lines}

Rules:
- SUMMARIZE ONLY. Do NOT add any new fact, number, or claim that is not in the list above.
- Keep the summary under 150 words.
- List up to 5 key points, each referencing fact numbers from the list.

Return ONLY valid JSON:
{{"summary": "...", "key_points": [{{"point": "...", "fact_refs": [1, 4]}}]}}"""

    result = complete_tier("mid", prompt)
    try:
        data = json.loads(result.get("content", "{}"))
        return {
            "summary": data.get("summary", ""),
            "key_points": data.get("key_points", []),
            "cost_usd": result.get("cost_usd", 0.0),
        }
    except Exception:
        return {"summary": "", "key_points": [], "cost_usd": result.get("cost_usd", 0.0)}