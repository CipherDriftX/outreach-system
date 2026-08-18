"""Template resolver — placeholder → fact resolution.

Every fact placeholder resolves to a lead_facts row; every signal placeholder
resolves to a column on the origin signals row. Resolution returns None when
the fact doesn't exist or grades below the floor — the builder then omits or
softens, NEVER hallucinates.
"""

from __future__ import annotations

from typing import Any

from src.nodes.offer.parser import Token, FactToken, SignalToken, ConditionalBlock


class Resolver:
    def __init__(
        self,
        facts: list[dict[str, Any]],
        signal: dict[str, Any],
        lead: dict[str, Any],
        grade_floor: str = "moderate",
    ) -> None:
        self.facts = facts
        self.signal = signal
        self.lead = lead
        self.grade_floor = grade_floor
        self.resolved_fact_ids: list[str] = []
        self.unresolved: list[str] = []

    def resolve_fact(self, token: FactToken) -> tuple[str | None, str | None]:
        """Return (resolved_text, fact_id). None text = couldn't resolve."""
        matches = [
            f for f in self.facts if f.get("fact_type") == token.fact_type
        ]

        # Grade filter — facts below the floor cannot back a confident claim
        grade_rank = {"strong": 2, "moderate": 1, "weak": 0}
        floor_rank = grade_rank.get(self.grade_floor, 1)
        qualifying = [
            f for f in matches
            if grade_rank.get(f.get("grade") or "weak", 0) >= floor_rank
        ]
        if not qualifying and matches:
            # Softening path: only gap_hypothesis may fall back to any grade
            if token.fact_type == "gap_hypothesis":
                qualifying = matches
            else:
                self.unresolved.append(token.key)
                return None, None

        if not qualifying:
            self.unresolved.append(token.key)
            return None, None

        fact = max(
            qualifying,
            key=lambda f: (
                grade_rank.get(f.get("grade") or "weak", 0),
                f.get("corroboration_count", 0),
            ),
        )
        self.resolved_fact_ids.append(fact["id"])

        text = fact["fact"]
        if token.modifier == "summary" or token.key == "gap_hypothesis_summary":
            text = _first_sentence(text)
        return text, fact["id"]

    def resolve_signal(self, token: SignalToken) -> str | None:
        value = self.signal.get(token.field)
        if value is None:
            self.unresolved.append(token.key)
            return None
        if token.key == "signal_raw_text_snippet":
            return str(value)[:160] + ("…" if len(str(value)) > 160 else "")
        return str(value)

    def resolve_conditional(self, block: ConditionalBlock) -> bool:
        matches = [
            f for f in self.facts if f.get("fact_type") == block.condition_fact_type
        ]
        if block.condition_value == "any":
            return len(matches) > 0
        if block.condition_fact_type == "recent_activity" and block.condition_value in ("funding_or_hiring",):
            keywords = ["funding", "raised", "hires", "hiring", "appoints", "launches"]
            return any(
                any(k in (f.get("fact") or "").lower() for k in keywords)
                for f in matches
            )
        if block.condition_fact_type == "competitors" and block.condition_value == "switched_from":
            return any(
                "switch" in (f.get("fact") or "").lower()
                or "alternative" in (f.get("fact") or "").lower()
                for f in matches
            )
        return len(matches) > 0


def _first_sentence(text: str) -> str:
    for delim in (". ", ".\n", "! ", "?\n", "? "):
        idx = text.find(delim)
        if idx != -1:
            return text[: idx + 1].strip()
    return text.strip()