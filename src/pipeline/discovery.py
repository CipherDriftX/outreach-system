"""Stage 1: Signal Discovery Pipeline.

Finds signals across all active adapters, triages each one, returns a flat
list of signal dicts ready for Excel. No database, just in-memory state.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from src.adapters.signals.registry import all_adapters
from src.llm.cascade import complete_tier

logger = structlog.get_logger(__name__)

ICP_ROOT = (
    "Businesses with painful operational processes that are candidates "
    "for autonomous AI execution"
)


def discover(
    icp_root: str = ICP_ROOT,
    max_queries_per_adapter: int = 3,
    limit_adapters: list[str] | None = None,
    since: datetime | None = None,
) -> dict[str, Any]:
    try:
        from src.nodes.signal.taxonomy import build_taxonomy
        taxonomy = build_taxonomy(icp_root, "")
    except Exception:
        taxonomy = {"root": icp_root, "verticals": _default_verticals()}
    verticals = taxonomy.get("verticals", [])
    if not verticals:
        verticals = _default_verticals()

    adapters = all_adapters()
    if limit_adapters:
        adapters = [a for a in adapters if a.name in limit_adapters]

    all_signals: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    per_adapter_rounds: dict[str, int] = {}
    per_adapter_novelty: dict[str, list[float]] = {}

    for vertical in verticals:
        label = vertical.get("label", "unknown")
        intent_patterns = vertical.get("intent_patterns", ["looking for", "need", "automation", "struggling with"])
        adapter_names = vertical.get("adapters", [a.name for a in adapters])

        for adapter in adapters:
            if adapter.name not in adapter_names:
                continue

            for query_idx in range(max_queries_per_adapter):
                query = _generate_query(vertical, intent_patterns, query_idx)
                if not query:
                    break

                per_adapter_rounds[adapter.name] = per_adapter_rounds.get(adapter.name, 0) + 1

                try:
                    raw = adapter.search(query, since)
                except Exception as exc:
                    logger.warning("adapter_search_failed", adapter=adapter.name, error=str(exc))
                    continue

                new_count = 0
                for s in raw:
                    if s["url"] not in seen_urls:
                        seen_urls.add(s["url"])
                        s["matched_pattern"] = query
                        triage = _triage(s, icp_root)
                        s["triage_score"] = triage["score"]
                        s["triage_reason"] = triage["reasoning"]
                        s["signal_id"] = str(uuid.uuid4())
                        s["captured_at"] = datetime.now(timezone.utc).isoformat()
                        all_signals.append(s)
                        new_count += 1

                novelty = new_count / max(len(raw), 1)
                history = per_adapter_novelty.setdefault(adapter.name, [])
                history.append(novelty)

                if len(history) >= 3 and all(n <= 0.1 for n in history[-3:]):
                    break

    all_signals.sort(key=lambda s: (s.get("triage_score", 0), s.get("captured_at", "")), reverse=True)
    return {
        "signals": all_signals,
        "taxonomy": taxonomy,
        "per_adapter_rounds": per_adapter_rounds,
        "per_adapter_novelty": per_adapter_novelty,
    }


def _generate_query(vertical: dict[str, Any], patterns: list[str], idx: int) -> str | None:
    if idx < len(patterns):
        label = vertical.get("label", "").replace("_", " ")
        return f"{patterns[idx]} {label}"
    if idx == len(patterns):
        return f"{patterns[0]} automation operational"
    return None


def _triage(signal: dict, icp_root: str) -> dict[str, Any]:
    text = signal.get("raw_text", "").lower()
    # Keyword heuristic as fallback when LLM unavailable
    intent_keywords = [
        "looking for", "need", "automation", "struggling", "hiring",
        "recommend", "does anyone", "frustrated with", "wish we had",
        "any tools", "switching from", "alternative",
    ]
    keyword_hits = sum(1 for kw in intent_keywords if kw in text)
    heuristic_score = min(3, keyword_hits)

    try:
        result = complete_tier("cheap", _triage_prompt(signal, icp_root))
        data = json.loads(result.get("content", "{}"))
        return {
            "score": max(0, min(3, int(data.get("score", heuristic_score)))),
            "reasoning": data.get("reasoning", f"keyword heuristic: {keyword_hits} hits"),
        }
    except Exception:
        return {
            "score": heuristic_score,
            "reasoning": f"keyword heuristic: {keyword_hits} intent keywords matched",
        }


def _triage_prompt(signal: dict, icp_root: str) -> str:
    return f"""Score this signal on relevance.

Our ICP: {icp_root}

Signal:
Source: {signal.get('source_name')} ({signal.get('source_type')})
Text: {signal.get('raw_text', '')[:400]}

0 = not relevant  1 = potentially relevant  2 = relevant  3 = high-confidence match
Return ONLY valid JSON: {{"score": 0-3, "reasoning": "one sentence"}}"""


def _default_verticals() -> list[dict[str, Any]]:
    return [
        {
            "label": "forum_posts",
            "description": "Help-seeking posts in forums and Q&A sites",
            "intent_patterns": ["does anyone know", "looking for", "recommend", "struggling with"],
            "adapters": ["reddit", "hackernews", "stackexchange"],
        },
        {
            "label": "social_threads",
            "description": "Social media posts expressing needs",
            "intent_patterns": ["does anyone", "looking for", "any tools", "frustrated with"],
            "adapters": ["twitter", "bluesky"],
        },
        {
            "label": "marketplace_gigs",
            "description": "Explicit needs posted with budgets",
            "intent_patterns": ["need someone to", "looking for a developer", "build a", "automate"],
            "adapters": ["upwork"],
        },
        {
            "label": "dev_activity",
            "description": "Issues, discussions, feature requests on GitHub",
            "intent_patterns": ["feature request", "need a way to", "is there a tool", "wish we had"],
            "adapters": ["github"],
        },
    ]