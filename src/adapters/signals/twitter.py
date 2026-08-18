"""X/Twitter signal adapter — recent search via API v2.

Requires TWITTER_BEARER_TOKEN. Degrades to no-op when the token is missing
rather than crashing the discovery graph.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from src.adapters.signals.base import RawSignal
from src.config import get_config

BASE = "https://api.twitter.com/2"


class TwitterAdapter:
    name = "twitter"
    source_type = "social_post"

    def __init__(self) -> None:
        self._calls = 0

    def _available(self) -> bool:
        return bool(get_config().twitter.bearer_token)

    def search(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        if not self._available():
            return []
        self._calls += 1

        params: dict[str, Any] = {
            "query": f"{query} -is:retweet -is:reply lang:en",
            "max_results": 25,
            "tweet.fields": "author_id,created_at,text",
            "expansions": "author_id",
            "user.fields": "username",
        }
        if since:
            params["start_time"] = since.isoformat()

        try:
            resp = httpx.get(
                f"{BASE}/tweets/search/recent",
                params=params,
                headers={"Authorization": f"Bearer {get_config().twitter.bearer_token}"},
                timeout=15.0,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
        except httpx.HTTPError:
            return []

        users = {
            u["id"]: u.get("username")
            for u in data.get("includes", {}).get("users", [])
        }
        results: list[RawSignal] = []
        for tweet in data.get("data", []):
            created = tweet.get("created_at")
            posted_at = (
                datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created
                else None
            )
            author_id = tweet.get("author_id")
            results.append(
                RawSignal(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=f"https://x.com/{users.get(author_id, 'i')}/status/{tweet['id']}",
                    author_handle=users.get(author_id),
                    raw_text=tweet.get("text", ""),
                    posted_at=posted_at,
                    matched_pattern="",
                )
            )
        return results

    def check_quota(self) -> tuple[int, int]:
        return (self._calls, 50)