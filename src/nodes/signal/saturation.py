"""Per-adapter saturation check for Node 1.

A source is saturated when it stops finding genuinely new signals.
Measured as novelty rate (new / total) over consecutive rounds.
"""

from __future__ import annotations

from typing import Any


def check_adapter_saturation(
    adapter_name: str,
    novelty_history: list[float],
) -> dict[str, Any]:
    novelty_threshold = 0.05
    consecutive_window = 3

    saturated = False
    if len(novelty_history) >= consecutive_window:
        recent = novelty_history[-consecutive_window:]
        if all(n <= novelty_threshold for n in recent):
            saturated = True

    return {
        "adapter": adapter_name,
        "saturated": saturated,
        "latest_novelty": novelty_history[-1] if novelty_history else 1.0,
        "novelty_history": novelty_history,
        "reason": (
            f"Novelty below {novelty_threshold} for {consecutive_window} consecutive rounds"
            if saturated
            else "still finding new signals"
        ),
    }


def is_vertical_saturated(
    adapter_statuses: list[dict[str, Any]],
) -> tuple[bool, str]:
    if not adapter_statuses:
        return False, "no adapters checked"

    all_saturated = all(a.get("saturated", False) for a in adapter_statuses)
    if all_saturated:
        return True, "all adapters saturated"

    return False, "some adapters still finding signals"