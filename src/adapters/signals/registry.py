"""Adapter registry — auto-discovers and instantiates signal source adapters."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from src.adapters.signals.base import SignalSourceAdapter

_ADAPTERS: dict[str, SignalSourceAdapter] = {}
_loaded = False

_ADAPTER_MODULES = [
    "src.adapters.signals.reddit",
    "src.adapters.signals.twitter",
    "src.adapters.signals.hackernews",
    "src.adapters.signals.stackexchange",
    "src.adapters.signals.upwork",
    "src.adapters.signals.github_",
    "src.adapters.signals.bluesky",
]


def _load_all() -> None:
    global _loaded
    if _loaded:
        return
    for module_name in _ADAPTER_MODULES:
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and attr.__module__ == module_name
                    and attr.__name__.endswith("Adapter")
                    and hasattr(attr, "search")
                    and hasattr(attr, "check_quota")
                ):
                    instance = attr()
                    _ADAPTERS[instance.name] = instance
        except ImportError:
            continue
    _loaded = True


def get_adapter(name: str) -> SignalSourceAdapter:
    _load_all()
    if name not in _ADAPTERS:
        raise KeyError(f"Unknown adapter: {name}. Available: {sorted(_ADAPTERS.keys())}")
    return _ADAPTERS[name]


def list_adapters() -> list[dict[str, Any]]:
    _load_all()
    return [
        {
            "name": a.name,
            "source_type": a.source_type,
        }
        for a in _ADAPTERS.values()
    ]


def all_adapters() -> list[SignalSourceAdapter]:
    _load_all()
    return list(_ADAPTERS.values())