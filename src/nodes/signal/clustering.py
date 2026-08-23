"""Community detection for signal split detection.

When a vertical produces diverse signals, Louvain community detection groups
them by similarity. LLM judges: genuine sub-vertical or noise?
"""

from __future__ import annotations

import json
import networkx as nx
from typing import Any

from src.llm.cascade import complete_tier


def detect_clusters(
    signals: list[dict[str, Any]],
    min_cluster_size: int = 5,
    min_distinctness: float = 0.3,
) -> list[dict[str, Any]]:
    if len(signals) < min_cluster_size * 2:
        return []

    G = nx.Graph()

    for i, s1 in enumerate(signals):
        G.add_node(i)
        for j in range(i + 1, len(signals)):
            s2 = signals[j]
            weight = _similarity(s1, s2)
            if weight > 0.1:
                G.add_edge(i, j, weight=weight)

    if G.number_of_edges() == 0:
        return []

    try:
        communities = nx.community.louvain_communities(G, seed=42)
    except Exception:
        return []

    candidates = []
    for i, community in enumerate(communities):
        if len(community) < min_cluster_size:
            continue

        # Compute distinctness: intra / inter edge weight ratio
        subgraph = G.subgraph(community)
        intra_weight = sum(
            d.get("weight", 0) for _, _, d in subgraph.edges(data=True)
        ) / max(subgraph.number_of_edges(), 1)

        inter_edges = 0
        inter_weight = 0.0
        for u in community:
            for v in set(G.nodes()) - community:
                if G.has_edge(u, v):
                    inter_edges += 1
                    inter_weight += G[u][v].get("weight", 0)
        avg_inter = inter_weight / max(inter_edges, 1)

        distinctness = intra_weight / max(avg_inter, 0.001)
        if distinctness < min_distinctness:
            continue

        # Collect sample signals for LLM judgment
        sample = [signals[idx] for idx in list(community)[:5]]

        candidates.append(
            {
                "cluster_id": i,
                "size": len(community),
                "distinctness": round(distinctness, 3),
                "sample_signals": [
                    {"text": s.get("raw_text", "")[:200], "matched_pattern": s.get("matched_pattern", "")}
                    for s in sample
                ],
            }
        )

    return sorted(candidates, key=lambda c: c["distinctness"], reverse=True)


def judge_clusters(
    candidates: list[dict[str, Any]],
    vertical_label: str,
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    sample = candidates[:3]

    prompt = f"""The signal vertical "{vertical_label}" produced these signal clusters.

For each cluster below, decide: is this a GENUINELY distinct sub-vertical a researcher
would care about, or just algorithmic noise?

If genuine: give it a short label (snake_case) and a description.
If noise: respond with {{"label": null, "description": "noise"}}.

Clusters:
{json.dumps(sample, indent=2)}

Return ONLY valid JSON array of judgments:
[{{"cluster_id": 0, "label": "sub_vertical_name", "description": "..."}}, ...]"""

    result = complete_tier("frontier", prompt)
    try:
        judgments = json.loads(result.get("content", "[]"))
        if isinstance(judgments, list):
            return [j for j in judgments if j.get("label") is not None and j.get("label") != "noise"]
    except Exception:
        pass

    return []


def _similarity(s1: dict[str, Any], s2: dict[str, Any]) -> float:
    """Simple text-overlap similarity. Replace with embeddings for production."""
    words1 = set(s1.get("raw_text", "").lower().split())
    words2 = set(s2.get("raw_text", "").lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


# Make nx.community available via monkeypatch if needed
if not hasattr(nx, "community"):
    try:
        import networkx.algorithms.community as nx_community
        nx.community = nx_community
    except ImportError:
        pass