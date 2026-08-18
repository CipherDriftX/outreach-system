"""Enrichment adapter protocol.

Node 2 Track A gathers obvious facts about a lead from an enrichment tool.
The web-search implementation uses direct search + LLM extraction at zero
incremental cost. A paid tool (Clay, Apollo) is a drop-in adapter later.
"""

from __future__ import annotations

from typing import Protocol, TypedDict


class EnrichmentFact(TypedDict):
    fact: str
    fact_type: str          # company_basics | contact_details | pain_signals | tech_stack | competitors | recent_activity | social_graph
    source_url: str | None
    observed_at: str | None


class EnrichmentResult(TypedDict):
    company_name: str | None
    contact_name: str | None
    contact_email: str | None
    website: str | None
    facts: list[EnrichmentFact]


class EnrichmentAdapter(Protocol):
    name: str

    def enrich(self, lead: dict, signal: dict) -> EnrichmentResult: ...