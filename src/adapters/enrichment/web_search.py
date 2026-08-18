"""Web-search enrichment — zero-cost Track A source.

Uses DuckDuckGo Instant Answer / HTML search (no key) and LLM extraction to
pull obvious facts: company basics, contact details, tech stack, recent
activity. Every extracted fact carries its source URL.
"""

from __future__ import annotations

import json
import structlog
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import httpx

from src.adapters.enrichment.base import EnrichmentFact, EnrichmentResult
from src.llm.cascade import complete_tier

logger = structlog.get_logger(__name__)


class WebSearchEnrichment:
    name = "web_search"

    def enrich(self, lead: dict, signal: dict) -> EnrichmentResult:
        query_basis = lead.get("company_name") or signal.get("author_handle") or ""
        if not query_basis:
            return EnrichmentResult(
                company_name=None,
                contact_name=None,
                contact_email=None,
                website=None,
                facts=[],
            )

        searches = [
            f"{query_basis} company",
            f"{query_basis} funding",
            f"{query_basis} hiring",
        ]

        all_snippets: list[dict[str, Any]] = []
        for query in searches:
            try:
                snippets = self._search(query)
                all_snippets.extend(snippets)
            except httpx.HTTPError:
                logger.warning("enrichment_search_failed", query=query)

        facts = self._extract_facts(query_basis, all_snippets)

        return EnrichmentResult(
            company_name=lead.get("company_name"),
            contact_name=lead.get("contact_name"),
            contact_email=lead.get("contact_email"),
            website=None,
            facts=facts,
        )

    def _search(self, query: str) -> list[dict[str, Any]]:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (outreach-os enrichment)"},
            timeout=15.0,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []

        results: list[dict[str, Any]] = []
        # Light HTML extraction of result snippets
        import re

        snippet_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        for match in snippet_pattern.finditer(resp.text):
            results.append(
                {
                    "url": match.group(1),
                    "title": re.sub(r"<[^>]+>", "", match.group(2)).strip(),
                    "snippet": re.sub(r"<[^>]+>", "", match.group(3)).strip(),
                }
            )
        return results[:10]

    def _extract_facts(
        self, entity: str, snippets: list[dict[str, Any]]
    ) -> list[EnrichmentFact]:
        if not snippets:
            return []

        context = "\n".join(
            f"- [{s.get('title', '')}] ({s.get('url', '')}): {s.get('snippet', '')[:300]}"
            for s in snippets[:15]
        )

        prompt = f"""Extract verifiable facts about "{entity}" from these search results.

Rules:
- ONLY extract facts explicitly stated in the snippets. NEVER infer or guess.
- Each fact must carry the URL of the snippet it came from.
- Classify each fact: company_basics, contact_details, pain_signals, tech_stack,
  competitors, recent_activity, social_graph.

Search results:
{context[:6000]}

Return ONLY valid JSON:
{{"facts": [{{"fact": "...", "fact_type": "...", "source_url": "..."}}]}}"""

        result = complete_tier("mid", prompt)
        try:
            data = json.loads(result.get("content", "{}"))
            facts = data.get("facts", [])
            if not isinstance(facts, list):
                return []
            return [
                EnrichmentFact(
                    fact=f.get("fact", "")[:500],
                    fact_type=f.get("fact_type", "observation"),
                    source_url=f.get("source_url"),
                    observed_at=datetime.now(timezone.utc).isoformat(),
                )
                for f in facts
                if f.get("fact")
            ]
        except (json.JSONDecodeError, TypeError):
            return []