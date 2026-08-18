"""Split detection for the signal taxonomy.

Runs clustering on a vertical's accumulated signals, asks LLM to judge
genuine sub-verticals, and returns new verticals to insert into the taxonomy.
"""

from __future__ import annotations

from typing import Any

from src.nodes.signal.clustering import detect_clusters, judge_clusters


def detect_splits(
    vertical: dict[str, Any],
    vertical_signals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(vertical_signals) < 10:
        return []

    candidates = detect_clusters(vertical_signals)
    if not candidates:
        return []

    judged = judge_clusters(candidates, vertical.get("label", "unknown"))
    if not judged:
        return []

    new_verticals: list[dict[str, Any]] = []
    for j in judged:
        new_verticals.append(
            {
                "label": j.get("label", f"{vertical.get('label', 'v')}_sub"),
                "description": j.get("description", "Auto-detected sub-vertical"),
                "intent_patterns": vertical.get("intent_patterns", []),
                "adapters": vertical.get("adapters", []),
                "parent_label": vertical.get("label"),
                "split_method": "graph_cluster",
            }
        )

    return new_verticals