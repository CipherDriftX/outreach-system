"""Offer builder — fills the user's template from resolved research.

Output: a filled subject + body with resolved_fact_ids tracking. Every
resolved value traces to a lead_facts.id or signals row — the linter can
verify the trace deterministically.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from src.nodes.offer.parser import (
    ConditionalBlock,
    FactToken,
    LiteralToken,
    SignalToken,
    Token,
    parse_template,
)
from src.nodes.offer.resolver import Resolver


def build_offer(
    template_text: str,
    lead: dict[str, Any],
    signal: dict[str, Any],
    facts: list[dict[str, Any]],
    grade_floor: str = "moderate",
) -> dict[str, Any]:
    tokens = parse_template(template_text)
    resolver = Resolver(facts, signal, lead, grade_floor=grade_floor)

    body_parts = _render_tokens(tokens, resolver)

    body = "".join(body_parts).strip()
    body = _collapse_blank_lines(body)

    subject = _derive_subject(body) or "Quick question"

    return {
        "subject": subject,
        "body": body,
        "resolved_fact_ids": resolver.resolved_fact_ids,
        "unresolved_placeholders": resolver.unresolved,
        "fully_resolved": len(resolver.unresolved) == 0,
    }


def _render_tokens(tokens: list[Token], resolver: Resolver) -> list[str]:
    parts: list[str] = []
    for token in tokens:
        if isinstance(token, LiteralToken):
            parts.append(token.text)
        elif isinstance(token, FactToken):
            text, _ = resolver.resolve_fact(token)
            if text:
                parts.append(text)
            else:
                parts.append(_omit_line(token.key))
        elif isinstance(token, SignalToken):
            text = resolver.resolve_signal(token)
            parts.append(text if text else _omit_line(token.key))
        elif isinstance(token, ConditionalBlock):
            if resolver.resolve_conditional(token):
                parts.extend(_render_tokens(token.tokens, resolver))
    return parts


def _omit_line(key: str) -> str:
    """When a fact can't be resolved, the sentence it belonged to must not
    render as a fragment. Emit a marker so _collapse_blank_lines drops the
    whole line it was on."""
    return f"[[UNRESOLVED:{key}]]"


def _collapse_blank_lines(text: str) -> str:
    lines = text.split("\n")
    kept = []
    for line in lines:
        if "[[UNRESOLVED:" in line:
            continue
        kept.append(line)
    # Collapse 3+ newlines into 2
    collapsed = re.sub(r"\n{3,}", "\n\n", "\n".join(kept))
    return collapsed.strip()


def _derive_subject(body: str) -> str | None:
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("Subject:"):
            return line.replace("Subject:", "", 1).strip()
        if line.startswith("subject:"):
            return line.replace("subject:", "", 1).strip()
    return None