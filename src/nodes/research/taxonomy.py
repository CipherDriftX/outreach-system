"""Per-lead research taxonomy builder.

Given a signal and what we already know, the LLM proposes what to research
about this specific lead. Depth-1 verticals are seeded (llm_seed); deeper
verticals are earned from evidence via split detection.
"""

from __future__ import annotations

import json
from typing import Any

from src.llm.cascade import complete_tier


def build_lead_taxonomy(lead: dict, signal: dict) -> dict[str, Any]:
    prompt = f"""Design a research plan for one specific lead.

Lead info:
- Company: {lead.get('company_name') or 'unknown'}
- Contact: {lead.get('contact_name') or 'unknown'}
- Contact email: {lead.get('contact_email') or 'unknown'}

Origin signal (why this lead exists):
- Source: {signal.get('source_name')} ({signal.get('source_type')})
- Author: {signal.get('author_handle') or 'unknown'}
- Text: {signal.get('raw_text', '')[:800]}

Produce 6-9 depth-1 research verticals. Each vertical is one dimension of
"what should we learn about this lead to write a truly personalized offer".

Verticals must cover:
1. Company basics (size, industry, funding, location)
2. Contact details (role, seniority, history, public posts)
3. Pain signals (what they've complained about or asked for)
4. Tech stack / tools (what they use)
5. Competitors / alternatives (what they switched from)
6. Recent activity (hires, launches, funding)
7. Social graph (who they interact with)

For each: label (snake_case), description, and 2-3 example search queries.

Return ONLY valid JSON:
{{"verticals": [{{"label": "...", "description": "...", "queries": ["..."]}}]}}"""

    result = complete_tier("mid", prompt)
    try:
        data = json.loads(result.get("content", "{}"))
        verticals = data.get("verticals", [])
        if isinstance(verticals, list) and verticals:
            return {
                "verticals": verticals,
                "llm_seed": True,
                "cost_usd": result.get("cost_usd", 0.0),
            }
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "verticals": _default_verticals(),
        "llm_seed": True,
        "cost_usd": result.get("cost_usd", 0.0),
    }


def _default_verticals() -> list[dict[str, Any]]:
    return [
        {
            "label": "company_basics",
            "description": "Company size, industry, funding, location",
            "queries": ["company profile", "about us", "funding round"],
        },
        {
            "label": "contact_details",
            "description": "Role, seniority, history of the contact person",
            "queries": ["linkedin profile", "role at company", "career history"],
        },
        {
            "label": "pain_signals",
            "description": "Complaints, feature requests, public expressions of pain",
            "queries": ["struggling with", "looking for", "frustrated with"],
        },
        {
            "label": "tech_stack",
            "description": "Tools, platforms, integrations they use",
            "queries": ["tech stack", "uses software", "tools used"],
        },
        {
            "label": "competitors",
            "description": "Who they compete with, what they switched from",
            "queries": ["competitors", "alternatives", "switched from"],
        },
        {
            "label": "recent_activity",
            "description": "New hires, launches, funding events",
            "queries": ["announces", "raises funding", "hires"],
        },
        {
            "label": "social_graph",
            "description": "Who they interact with publicly",
            "queries": ["mentions", "partnership", "collaboration"],
        },
    ]