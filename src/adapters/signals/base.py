"""Signal source adapter protocol.

Every signal source — Reddit, X, HN, Stack Exchange, Upwork, GitHub — is one
adapter behind this interface. A new source later is a new adapter file, not a
new architecture.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, TypedDict, runtime_checkable


class RawSignal(TypedDict):
    source_type: str          # 'forum_post' | 'job_posting' | 'marketplace_gig' | 'review' | 'social_post' | 'dev_activity' | 'news_event' | 'relationship_context'
    source_name: str          # 'reddit' | 'twitter' | 'hackernews' | 'stackexchange' | 'upwork' | 'github' | ...
    url: str
    author_handle: str | None
    raw_text: str             # verbatim — this is what justifies the outreach existing at all
    posted_at: datetime | None
    matched_pattern: str      # which intent pattern fired


@runtime_checkable
class SignalSourceAdapter(Protocol):
    name: str
    source_type: str

    def search(self, query: str, since: datetime | None = None) -> list[RawSignal]: ...

    def check_quota(self) -> tuple[int, int]: ...  # (used_this_run, ceiling)
