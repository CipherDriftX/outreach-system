"""Evidence grading — the deterministic four-axis honesty layer.

Grading is PURE ARITHMETIC over lead_facts. The LLM's confidence never moves
the grade. Four axes:
- Corroboration: how many independent entities support it (>=3 → strong; 1 → structurally weak)
- Consistency: variance across supporting evidence
- Recency: freshness in days
- Effect size: how far above baseline
"""

from __future__ import annotations

from typing import Any


def grade_fact(
    fact: dict[str, Any],
    corroboration_count: int | None = None,
    consistency: float | None = None,
    recency_days: int | None = None,
    effect_size: float | None = None,
) -> dict[str, Any]:
    corr = corroboration_count if corroboration_count is not None else fact.get("corroboration_count", 1)
    cons = consistency if consistency is not None else fact.get("consistency")
    recency = recency_days if recency_days is not None else fact.get("recency_days")
    effect = effect_size if effect_size is not None else fact.get("effect_size")

    scores: dict[str, int] = {}

    # Corroboration axis
    if corr >= 3:
        scores["corroboration"] = 2  # strong
    elif corr >= 2:
        scores["corroboration"] = 1  # moderate
    else:
        scores["corroboration"] = 0  # structurally weak

    # Consistency axis
    if cons is None:
        scores["consistency"] = 1  # unknown → moderate
    elif cons >= 0.8:
        scores["consistency"] = 2
    elif cons >= 0.5:
        scores["consistency"] = 1
    else:
        scores["consistency"] = 0

    # Recency axis
    if recency is None:
        scores["recency"] = 1
    elif recency <= 30:
        scores["recency"] = 2
    elif recency <= 90:
        scores["recency"] = 1
    else:
        scores["recency"] = 0

    # Effect size axis
    if effect is None:
        scores["effect_size"] = 1
    elif effect >= 2.0:
        scores["effect_size"] = 2
    elif effect >= 1.2:
        scores["effect_size"] = 1
    else:
        scores["effect_size"] = 0

    total = sum(scores.values())

    if total >= 7:
        grade = "strong"
    elif total >= 4:
        grade = "moderate"
    else:
        grade = "weak"

    return {
        "grade": grade,
        "axis_scores": scores,
        "total": total,
    }


def grade_all_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**f, "grade": grade_fact(f)["grade"], "axis_scores": grade_fact(f)["axis_scores"]}
        for f in facts
    ]


def update_fact_grades(lead_id: str) -> list[dict[str, Any]]:
    from src.db.connection import get_connection, put_connection
    from src.db.queries import get_lead_facts

    facts = get_lead_facts(lead_id)
    conn = get_connection()
    try:
        for f in facts:
            graded = grade_fact(
                f,
                corroboration_count=f.get("corroboration_count", 1),
                consistency=f.get("consistency"),
                recency_days=f.get("recency_days"),
                effect_size=f.get("effect_size"),
            )
            cur = conn.cursor()
            cur.execute(
                "UPDATE lead_facts SET grade = %s WHERE id = %s",
                [graded["grade"], f["id"]],
            )
            cur.close()
        conn.commit()
    finally:
        put_connection(conn)
    return get_lead_facts(lead_id)