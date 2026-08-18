"""Saturation check tests."""

from src.nodes.signal.saturation import check_adapter_saturation, is_vertical_saturated


def test_saturates_after_flat_novelty():
    history = [0.4, 0.1, 0.02, 0.01, 0.0]
    result = check_adapter_saturation("reddit", history)
    assert result["saturated"]
    assert result["reason"].startswith("Novelty below")


def test_not_saturated_with_recent_high_novelty():
    history = [0.4, 0.1, 0.02, 0.01, 0.9]
    result = check_adapter_saturation("reddit", history)
    assert not result["saturated"]


def test_not_saturated_with_short_history():
    history = [0.01, 0.0]
    result = check_adapter_saturation("reddit", history)
    assert not result["saturated"]


def test_vertical_saturated_only_when_all_adapters():
    statuses = [
        {"saturated": True},
        {"saturated": True},
    ]
    saturated, _ = is_vertical_saturated(statuses)
    assert saturated

    statuses = [
        {"saturated": True},
        {"saturated": False},
    ]
    saturated, _ = is_vertical_saturated(statuses)
    assert not saturated