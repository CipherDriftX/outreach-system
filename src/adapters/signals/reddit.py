"""Reddit signal adapter — help-seeking posts across subreddits.

Uses old.reddit.com search which still allows unauthenticated access,
falling back to OAuth when client credentials are configured.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from src.adapters.signals.base import RawSignal
from src.config import get_config

UA = "outreach-os:plarix:v0.2 (signal discovery)"


class RedditAdapter:
    name = "reddit"
    source_type = "forum_post"

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expiry = 0.0
        self._calls = 0

    def _ensure_token(self) -> bool:
        config = get_config()
        if not config.reddit.client_id or not config.reddit.client_secret:
            return False
        if self._token and time.time() < self._token_expiry:
            return True
        resp = httpx.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(config.reddit.client_id, config.reddit.client_secret),
            headers={"User-Agent": UA},
            timeout=15.0,
        )
        if resp.status_code != 200:
            return False
        data = resp.json()
        self._token = data.get("access_token")
        self._token_expiry = time.time() + float(data.get("expires_in", 3600)) - 60
        return True

    def search(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        self._calls += 1
        auth = self._ensure_token()

        if auth:
            return self._search_oauth(query, since)
        return self._search_old_reddit(query, since)

    def _search_old_reddit(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        """old.reddit.com still serves .json search without auth."""
        results: list[RawSignal] = []
        try:
            resp = httpx.get(
                "https://old.reddit.com/search.json",
                params={"q": query, "sort": "new", "limit": 25, "restrict_sr": "off"},
                headers={"User-Agent": UA},
                timeout=15.0,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
        except httpx.HTTPError:
            return []

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            created_utc = post.get("created_utc")
            posted_at = (
                datetime.fromtimestamp(created_utc, tz=timezone.utc)
                if created_utc
                else None
            )
            if since and posted_at and posted_at < since:
                continue
            text = post.get("selftext") or ""
            title = post.get("title") or ""
            full = f"{title}\n\n{text}".strip()
            if not full:
                continue
            results.append(
                RawSignal(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=f"https://www.reddit.com{post.get('permalink', '')}",
                    author_handle=post.get("author"),
                    raw_text=full,
                    posted_at=posted_at,
                    matched_pattern="",
                )
            )
        return results

    def _search_oauth(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        results: list[RawSignal] = []
        headers = {
            "User-Agent": UA,
            "Authorization": f"bearer {self._token}",
        }
        try:
            resp = httpx.get(
                "https://oauth.reddit.com/search",
                params={"q": query, "sort": "new", "limit": 25, "t": "month"},
                headers=headers,
                timeout=15.0,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
        except httpx.HTTPError:
            return []

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            created_utc = post.get("created_utc")
            posted_at = (
                datetime.fromtimestamp(created_utc, tz=timezone.utc)
                if created_utc
                else None
            )
            if since and posted_at and posted_at < since:
                continue
            text = post.get("selftext") or post.get("title") or ""
            if not text.strip():
                continue
            results.append(
                RawSignal(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=f"https://www.reddit.com{post.get('permalink', '')}",
                    author_handle=post.get("author"),
                    raw_text=text,
                    posted_at=posted_at,
                    matched_pattern="",
                )
            )
        return results

    def check_quota(self) -> tuple[int, int]:
        return (self._calls, 30)