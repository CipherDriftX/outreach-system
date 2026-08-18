"""Reddit signal adapter — help-seeking posts across subreddits.

Uses Reddit's public JSON endpoints (no auth needed for search), falling back
to OAuth app-only flow when client credentials are configured.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

from src.adapters.signals.base import RawSignal
from src.config import get_config

BASE = "https://www.reddit.com"
OAUTH = "https://oauth.reddit.com"
UA = "outreach-os:plarix:v0.1 (signal discovery)"


class RedditAdapter:
    name = "reddit"
    source_type = "forum_post"

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expiry = 0.0
        self._calls = 0

    def _client(self, authenticated: bool = False) -> httpx.Client:
        headers = {"User-Agent": UA}
        base = BASE
        if authenticated and self._ensure_token():
            headers["Authorization"] = f"bearer {self._token}"
            base = OAUTH
        return httpx.Client(base_url=base, headers=headers, timeout=15.0)

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
        results: list[RawSignal] = []
        auth = self._ensure_token()

        try:
            with self._client(auth) as client:
                resp = client.get(
                    "/search.json",
                    params={
                        "q": query,
                        "sort": "new",
                        "limit": 25,
                        "t": "month" if since is None else "all",
                    },
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
                    raw_text=f"{post.get('title', '')}\n\n{text}".strip(),
                    posted_at=posted_at,
                    matched_pattern="",  # filled by the intent-pattern matcher
                )
            )
        return results

    def check_quota(self) -> tuple[int, int]:
        # Reddit public JSON: ~60 req/min anonymous. We self-limit to 30/run.
        return (self._calls, 30)