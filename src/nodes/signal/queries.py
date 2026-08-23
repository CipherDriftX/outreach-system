"""Intent-pattern query generation per taxonomy leaf.

Expands each vertical's intent patterns into concrete search queries, combined
with the vertical's own language. Broad first, narrowed by what returned actual
signals. Never reissues an identical query.
"""

from __future__ import annotations

import json as _json
from typing import Any

from src.llm.cascade import complete_tier


def generate_intent_queries(
    vertical: dict[str, Any],
    previous_queries: list[str],
    successful_patterns: list[str],
) -> list[str]:
    if not previous_queries and not successful_patterns:
        return _seed_queries(vertical)

    # Expand: ask the cheap model to generate new queries from what worked
    prompt = f"""Generate 3-5 new search queries for finding {vertical.get("label")} signals.
The vertical context: {vertical.get("description", "")}

Queries already tried (DO NOT repeat these): {_json.dumps(previous_queries[-20:]) if previous_queries else "none"}
Patterns that returned results: {_json.dumps(successful_patterns[-5:]) if successful_patterns else "none"}

Return ONLY a JSON array of strings. Each string is a concrete search query."""

    result = complete_tier("cheap", prompt)
    try:
        queries = _json.loads(result.get("content", "[]"))
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            return [q for q in queries if q not in previous_queries]
    except Exception:
        pass
    return _seed_queries(vertical)


def _seed_queries(vertical: dict[str, Any]) -> list[str]:
    patterns = vertical.get("intent_patterns", [])
    label = vertical.get("label", "").replace("_", " ")
    queries: list[str] = []
    for pattern in patterns[:5]:
        queries.append(f"{pattern} {label}")
        queries.append(f"{pattern}")
    return queries