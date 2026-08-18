"""Evidence grading tests — the four-axis deterministic grader."""

from src.nodes.research.evidence import grade_fact


def test_strong_fact():
    result = grade_fact(
        {}, corroboration_count=3, consistency=0.9, recency_days=10, effect_size=2.5
    )
    assert result["grade"] == "strong"
    assert result["axis_scores"]["corroboration"] == 2
    assert result["axis_scores"]["consistency"] == 2
    assert result["axis_scores"]["recency"] == 2
    assert result["axis_scores"]["effect_size"] == 2


def test_single_corroboration_is_weak():
    result = grade_fact(
        {}, corroboration_count=1, consistency=0.9, recency_days=5, effect_size=2.0
    )
    assert result["axis_scores"]["corroboration"] == 0
    assert result["grade"] in ("moderate", "weak")


def test_stale_fact_downgraded():
    result = grade_fact(
        {}, corroboration_count=3, consistency=0.9, recency_days=400, effect_size=2.0
    )
    assert result["axis_scores"]["recency"] == 0
    assert result["grade"] != "strong"


def test_inconsistent_evidence_downgraded():
    result = grade_fact(
        {}, corroboration_count=3, consistency=0.3, recency_days=10, effect_size=2.0
    )
    assert result["axis_scores"]["consistency"] == 0


def test_no_metadata_is_weak():
    # Single source (corroboration=1), no consistency/recency/effect data.
    # Corroboration axis is structurally 0; unknowns score 1 each.
    # Total 3 < 4 → weak. A single-source, unverified fact must NOT grade
    # moderate — honesty is the point of this layer.
    result = grade_fact({})
    assert result["grade"] == "weak"


def test_weak_when_everything_bad():
    result = grade_fact(
        {}, corroboration_count=1, consistency=0.2, recency_days=500, effect_size=0.5
    )
    assert result["grade"] == "weak"


def test_llm_confidence_cannot_move_grade():
    # The grader takes no confidence argument at all — the only inputs are
    # the four deterministic axes. This is the design invariant.
    result = grade_fact({}, corroboration_count=1)
    assert "confidence" not in result
    assert result["grade"] == grade_fact({}, corroboration_count=1)["grade"]