"""Centralized configuration for Outreach OS CLI pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _load_governors() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "config" / "governors.yaml"
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


class OpenRouterConfig(BaseSettings):
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model_config = {"env_prefix": "OPENROUTER_"}


class RedditConfig(BaseSettings):
    client_id: str = ""
    client_secret: str = ""
    model_config = {"env_prefix": "REDDIT_"}


class TwitterConfig(BaseSettings):
    bearer_token: str = ""
    model_config = {"env_prefix": "TWITTER_"}


class GitHubConfig(BaseSettings):
    token: str = ""
    model_config = {"env_prefix": "GITHUB_"}


class StackExchangeConfig(BaseSettings):
    key: str = ""
    model_config = {"env_prefix": "STACKEXCHANGE_"}


class OutreachConfig(BaseSettings):
    log_level: str = "INFO"
    model_config = {"env_prefix": "OUTREACH_", "extra": "allow"}


class Config:
    def __init__(self) -> None:
        self.openrouter = OpenRouterConfig()
        self.reddit = RedditConfig()
        self.twitter = TwitterConfig()
        self.github = GitHubConfig()
        self.stackexchange = StackExchangeConfig()
        self.outreach = OutreachConfig()
        self.governors = _load_governors()

    @classmethod
    def from_env(cls) -> Config:
        return cls()


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config