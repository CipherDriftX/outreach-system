"""GitHub signal adapter — issues and discussions as dev-activity signals.

Public API, GITHUB_TOKEN optional (higher rate limit with it).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from src.adapters.signals.base import RawSignal
from src.config import get_config

BASE = "https://api.github.com"


class GitHubAdapter:
    name = "github"
    source_type = "dev_activity"

    def __init__(self) -> None:
        self._calls = 0

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        token = get_config().github.token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def search(self, query: str, since: datetime | None = None) -> list[RawSignal]:
        self._calls += 1
        q = query
        if since:
            q += f" created:>{since.strftime('%Y-%m-%d')}"
        try:
            resp = httpx.get(
                f"{BASE}/search/issues",
                params={"q": q, "sort": "created", "order": "desc", "per_page": 25},
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
        except httpx.HTTPError:
            return []

        results: list[RawSignal] = []
        for item in data.get("items", []):
            created = item.get("created_at")
            posted_at = (
                datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created
                else None
            )
            results.append(
                RawSignal(
                    source_type=self.source_type,
                    source_name=self.name,
                    url=item.get("html_url", ""),
                    author_handle=item.get("user", {}).get("login"),
                    raw_text=f"{item.get('title', '')}\n\n{item.get('body') or ''}".strip(),
                    posted_at=posted_at,
                    matched_pattern="",
                )
            )
        return results

    def check_quota(self) -> tuple[int, int]:
        return (self._calls, 30)