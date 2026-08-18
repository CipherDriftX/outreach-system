"""Upwork signal adapter — the most literal signal that exists.

A stated need with a budget attached. Public job search RSS/Atom feeds, no
auth required for browsing feed results.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import httpx

from src.adapters.signals.base import RawSignal

BASE = "https://www.upwork.com/ab/feed/jobs/rss"


class UpworkAdapter:
    name = "upwork"
    source_type = "marketplace_gig"

    def __init__(self) -> None:
        self._calls = 0

    def search(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        self._calls += 1
        try:
            resp = httpx.get(
                BASE,
                params={"q": query, "sort": "recency"},
                headers={"User-Agent": "Mozilla/5.0 (outreach-os signal discovery)"},
                timeout=20.0,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return []
        except httpx.HTTPError:
            return []

        try:
            root = ElementTree.fromstring(resp.content)
        except ElementTree.ParseError:
            return []

        results: list[RawSignal] = []
        for item in root.iter("item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            description = item.findtext("description") or ""
            pub_date = item.findtext("pubDate") or ""
            posted_at = None
            if pub_date:
                try:
                    posted_at = datetime.strptime(
                        pub_date, "%a, %d %b %Y %H:%M:%S %z"
                    )
                except ValueError:
                    posted_at = None
            if since and posted_at and posted_at < since:
                continue
            results.append(
                RawSignal(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=link,
                    author_handle=None,
                    raw_text=f"{title}\n\n{description}".strip(),
                    posted_at=posted_at,
                    matched_pattern="",
                )
            )
        return results

    def check_quota(self) -> tuple[int, int]:
        return (self._calls, 100)