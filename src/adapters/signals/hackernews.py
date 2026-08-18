"""Hacker News signal adapter — Ask HN, Show HN, job posts via Algolia API.

Free, no auth. The Algolia API is the canonical search interface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from src.adapters.signals.base import RawSignal

BASE = "https://hn.algolia.com/api/v1"


class HackerNewsAdapter:
    name = "hackernews"
    source_type = "forum_post"

    def __init__(self) -> None:
        self._calls = 0

    def search(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        self._calls += 1

        # Intent-pattern aware: Ask HN = help-seeking, Show HN = built something,
        # whoishiring threads = hiring signals.
        numeric_filters: list[str] = []
        if since:
            numeric_filters.append(f"created_at_i>{int(since.timestamp())}")

        params: dict[str, Any] = {
            "query": query,
            "tags": "story",
            "hitsPerPage": 25,
        }
        if numeric_filters:
            params["numericFilters"] = ",".join(numeric_filters)

        try:
            resp = httpx.get(f"{BASE}/search_by_date", params=params, timeout=15.0)
            if resp.status_code != 200:
                return []
            data = resp.json()
        except httpx.HTTPError:
            return []

        results: list[RawSignal] = []
        for hit in data.get("hits", []):
            created_i = hit.get("created_at_i")
            posted_at = (
                datetime.fromtimestamp(created_i, tz=timezone.utc)
                if created_i
                else None
            )
            text = hit.get("story_text") or hit.get("title") or ""
            if not text.strip():
                continue
            results.append(
                RawSignal(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    author_handle=hit.get("author"),
                    raw_text=f"{hit.get('title', '')}\n\n{text}".strip(),
                    posted_at=posted_at,
                    matched_pattern="",
                )
            )
        return results

    def check_quota(self) -> tuple[int, int]:
        return (self._calls, 500)