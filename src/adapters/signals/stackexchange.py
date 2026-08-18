"""Stack Exchange signal adapter — Q&A across the network.

Free API. Questions about tooling, process, and automation are demand signals.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from src.adapters.signals.base import RawSignal
from src.config import get_config

BASE = "https://api.stackexchange.com/2.3"
SITES = [
    "stackoverflow",
    "serverfault",
    "workplace",
    "softwareengineering",
]


class StackExchangeAdapter:
    name = "stackexchange"
    source_type = "forum_post"

    def __init__(self) -> None:
        self._calls = 0

    def search(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        results: list[RawSignal] = []
        config = get_config()

        params: dict[str, Any] = {
            "site": "stackoverflow",
            "order": "desc",
            "sort": "creation",
            "pagesize": 10,
            "intitle": query[:150],
            "filter": "withbody",
        }
        if since:
            params["fromdate"] = int(since.timestamp())
        if config.stackexchange.key:
            params["key"] = config.stackexchange.key

        for site in SITES:
            self._calls += 1
            params["site"] = site
            try:
                resp = httpx.get(f"{BASE}/search/advanced", params=params, timeout=15.0)
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except httpx.HTTPError:
                continue

            for item in data.get("items", []):
                created = item.get("creation_date")
                posted_at = (
                    datetime.fromtimestamp(created, tz=timezone.utc)
                    if created
                    else None
                )
                results.append(
                    RawSignal(
                        source_type=self.source_type,
                        source_name=self.name,
                        url=item.get("link", ""),
                        author_handle=item.get("owner", {}).get("display_name"),
                        raw_text=item.get("title", ""),
                        posted_at=posted_at,
                        matched_pattern="",
                    )
                )
        return results

    def check_quota(self) -> tuple[int, int]:
        return (self._calls, 300)