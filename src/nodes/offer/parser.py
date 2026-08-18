"""Template parser for the offer builder.

Parses the user's template text into tokens:
- literal text (rendered as-is)
- [fact_placeholder] — resolved against lead_facts by fact_type
- (signal_placeholder) — resolved against the origin signal row
- [if fact_type: value] ... [/if] — conditional block, rendered only if the
  referenced fact exists AND its grade meets the threshold

Conditionals nest. The parser is pure and deterministic — no LLM anywhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Union


@dataclass
class LiteralToken:
    text: str


@dataclass
class FactToken:
    key: str            # the raw placeholder text inside [..]
    fact_type: str      # mapped fact_type for lead_facts lookup
    modifier: str = ""  # e.g. "summary" in gap_hypothesis_summary


@dataclass
class SignalToken:
    key: str            # raw placeholder text inside (..)
    field: str          # mapped signals column


@dataclass
class ConditionalBlock:
    condition_fact_type: str
    condition_value: str
    tokens: list[Union[LiteralToken, FactToken, SignalToken, "ConditionalBlock"]] = field(default_factory=list)


Token = Union[LiteralToken, FactToken, SignalToken, ConditionalBlock]

# Fact placeholder → lead_facts.fact_type mapping
FACT_TYPE_MAP: dict[str, str] = {
    "company_name": "company_basics",
    "company_what_we_do": "company_basics",
    "contact_first_name": "contact_details",
    "contact_full_name": "contact_details",
    "contact_role": "contact_details",
    "pain_summary": "pain_signals",
    "pain_detail": "pain_signals",
    "tech_stack_primary_tools": "tech_stack",
    "tech_stack": "tech_stack",
    "competitor_name": "competitors",
    "recent_activity_detail": "recent_activity",
    "recent_activity": "recent_activity",
    "gap_hypothesis_summary": "gap_hypothesis",
    "gap_hypothesis_explanation": "gap_hypothesis",
    "gap_hypothesis_category": "gap_hypothesis",
    "social_graph": "social_graph",
    "relationship_context": "relationship_context",
}

# Signal placeholder → signals column mapping
SIGNAL_FIELD_MAP: dict[str, str] = {
    "signal_source_type": "source_type",
    "signal_source_name": "source_name",
    "signal_raw_text": "raw_text",
    "signal_raw_text_snippet": "raw_text",
    "signal_author_handle": "author_handle",
    "signal_url": "url",
    "signal_posted_at": "posted_at",
}

CONDITION_VALUE_MAP: dict[str, str] = {
    "any": "any",
    "funding_or_hiring": "recent_activity",
    "switched_from": "competitors",
    "exists": "any",
}

_FACT_RE = re.compile(r"\[([a-z_]+)\]")
_SIGNAL_RE = re.compile(r"\(([a-z_]+)\)")
_COND_OPEN_RE = re.compile(r"\[if\s+([a-z_]+)\s*:\s*([a-z_]+)\]")
_COND_CLOSE_RE = re.compile(r"\[/if\]")


def parse_template(template_text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(template_text)

    while i < n:
        fact_match = _FACT_RE.search(template_text, i)
        signal_match = _SIGNAL_RE.search(template_text, i)
        cond_match = _COND_OPEN_RE.search(template_text, i)

        candidates = []
        if fact_match:
            candidates.append((fact_match.start(), "fact"))
        if signal_match:
            candidates.append((signal_match.start(), "signal"))
        if cond_match:
            candidates.append((cond_match.start(), "cond"))

        if not candidates:
            tokens.append(LiteralToken(template_text[i:]))
            break

        start, kind = min(candidates, key=lambda c: c[0])

        if start > i:
            tokens.append(LiteralToken(template_text[i:start]))

        if kind == "fact":
            key = fact_match.group(1)
            tokens.append(
                FactToken(
                    key=key,
                    fact_type=FACT_TYPE_MAP.get(key, "observation"),
                    modifier=key.split("_")[-1] if key.startswith("gap_hypothesis") else "",
                )
            )
            i = fact_match.end()
        elif kind == "signal":
            key = signal_match.group(1)
            tokens.append(
                SignalToken(key=key, field=SIGNAL_FIELD_MAP.get(key, "raw_text"))
            )
            i = signal_match.end()
        else:
            fact_type = CONDITION_VALUE_MAP.get(cond_match.group(1), cond_match.group(1))
            cond_value = cond_match.group(2)
            inner_start = cond_match.end()

            # Find the matching [/if] — nesting-aware
            close_end = _find_matching_close(template_text, inner_start)
            if close_end is None:
                tokens.append(LiteralToken(template_text[i:]))
                break

            inner_tokens = parse_template(template_text[inner_start:close_end])
            tokens.append(
                ConditionalBlock(
                    condition_fact_type=fact_type,
                    condition_value=cond_value,
                    tokens=inner_tokens,
                )
            )
            i = close_end + len("[/if]")

    return tokens


def _find_matching_close(text: str, start: int) -> int | None:
    """Return the index of the [/if] that closes the block opening at `start`."""
    depth = 1
    j = start
    while j < len(text) and depth > 0:
        open_m = _COND_OPEN_RE.search(text, j)
        close_m = _COND_CLOSE_RE.search(text, j)
        if close_m is None:
            return None
        if open_m is not None and open_m.start() < close_m.start():
            depth += 1
            j = open_m.end()
        else:
            depth -= 1
            if depth == 0:
                return close_m.start()
            j = close_m.end()
    return None


def extract_placeholders(template_text: str) -> dict[str, list[str]]:
    """For the UI: list which placeholders a template uses."""
    tokens = parse_template(template_text)

    fact_keys: set[str] = set()
    signal_keys: set[str] = set()
    conditionals: set[str] = set()

    def walk(ts: list[Token]) -> None:
        for t in ts:
            if isinstance(t, FactToken):
                fact_keys.add(t.key)
            elif isinstance(t, SignalToken):
                signal_keys.add(t.key)
            elif isinstance(t, ConditionalBlock):
                conditionals.add(f"{t.condition_fact_type}:{t.condition_value}")
                walk(t.tokens)

    walk(tokens)
    return {
        "fact_placeholders": sorted(fact_keys),
        "signal_placeholders": sorted(signal_keys),
        "conditionals": sorted(conditionals),
    }