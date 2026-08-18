"""Bluesky signal adapter — public search via the AT Protocol API.

No auth needed for public search.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from src.adapters.signals.base import RawSignal

BASE = "https://public.api.bsky.app/xrpc"


class BlueskyAdapter:
    name = "bluesky"
    source_type = "social_post"

    def __init__(self) -> None:
        self._calls = 0

    def search(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        self._calls += 1
        params: dict[str, Any] = {
            "q": query,
            "sort": "latest",
            "limit": 25,
        }
        if since:
            params["since"] = since.isoformat()

        try:
            resp = httpx.get(
                f"{BASE}/app.bsky.feed.searchPosts", params=params, timeout=15.0
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
        except httpx.HTTPError:
            return []

        results: list[RawSignal] = []
        for post in data.get("posts", []):
            created = post.get("record", {}).get("createdAt")
            posted_at = (
                datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created
                else None
            )
            author = post.get("author", {})
            results.append(
                RawSignal(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=f"https://bsky.app/profile/{author.get('handle')}/post/{post.get('uri', '').split('/')[-1]}",
                    author_handle=author.get("handle"),
                    raw_text=post.get("record", {}).get("text", ""),
                    posted_at=posted_at,
                    matched_pattern="",
                )
            )
        return results

    def check_quota(self) -> tuple[int, int]:
        return (self._calls, 200)