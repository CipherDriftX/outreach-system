"""ICP Taxonomy builder for signal discovery.

Takes the business ICP root and generates depth-1 verticals via LLM.
Verticals are the distinct categories of signal sources — not customer segments.
The LLM seeds them before any data exists (honest about it — llm_seed flag).
"""

from __future__ import annotations

import json
from typing import Any

from src.llm.cascade import complete_tier


def build_taxonomy(icp_root: str, business_id: str) -> dict[str, Any]:
    prompt = f"""You are designing a signal-discovery taxonomy for an outreach system.

The business's ICP (ideal customer problem profile):
"{icp_root}"

Your job: produce depth-1 verticals — categories of places where people PUBLICLY express
needs that this business can solve. These are NOT customer segments. They are the TYPES
of public signals: forum posts, job postings, marketplace gigs, social posts, complaints,
dev activity, news events, etc.

Give me exactly 7-10 verticals. Each vertical:
- A label (short, like "forum_posts" or "job_postings")
- A description of what kinds of signals live here
- 3-4 example intent patterns ("looking for X", "struggling with X", "hiring X", etc.)
- Which adapter types map to this vertical (reddit, twitter, upwork, indeed, github, etc.)

Return ONLY valid JSON — no preamble, no explanation. Format:
{{"verticals": [
  {{"label": "...", "description": "...", "intent_patterns": ["...", "..."], "adapters": ["reddit", "twitter"]}},
  ...
]}}"""

    result = complete_tier("frontier", prompt)
    raw = result.get("content", "{}")

    try:
        data = json.loads(raw)
    except Exception:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        try:
            data = json.loads(raw)
        except Exception:
            data = {"verticals": _default_verticals()}

    return {
        "root": icp_root,
        "verticals": data.get("verticals", _default_verticals()),
        "llm_seed": True,
        "cost_usd": result.get("cost_usd", 0.0),
    }


def _default_verticals() -> list[dict[str, Any]]:
    return [
        {
            "label": "forum_posts",
            "description": "Help-seeking and discussion posts in forums and Q&A sites",
            "intent_patterns": ["does anyone know", "looking for", "recommend", "struggling with"],
            "adapters": ["reddit", "hackernews", "stackexchange"],
        },
        {
            "label": "social_threads",
            "description": "Social media posts and threads expressing needs or complaints",
            "intent_patterns": ["does anyone", "looking for", "any tools", "frustrated with", "switching from"],
            "adapters": ["twitter", "bluesky"],
        },
        {
            "label": "job_postings",
            "description": "Job listings that imply a process or capability gap",
            "intent_patterns": ["hiring", "looking for a", "we need someone to", "responsible for"],
            "adapters": ["indeed"],
        },
        {
            "label": "marketplace_gigs",
            "description": "Explicit needs posted with budgets on freelance marketplaces",
            "intent_patterns": ["need someone to", "looking for a developer", "build a", "automate"],
            "adapters": ["upwork"],
        },
        {
            "label": "complaints",
            "description": "Complaints about existing tools, competitors, or processes",
            "intent_patterns": ["doesn't work", "frustrated with", "switching from", "looking for alternative"],
            "adapters": ["reddit", "twitter"],
        },
        {
            "label": "dev_activity",
            "description": "Development activity: issues, discussions, feature requests on GitHub",
            "intent_patterns": ["feature request", "wish we had", "need a way to", "is there a tool"],
            "adapters": ["github"],
        },
        {
            "label": "news_events",
            "description": "Funding, executive hires, expansions signaling organizational change",
            "intent_patterns": ["raised", "funding", "appoints", "expansion", "launches"],
            "adapters": [],
        },
    ]