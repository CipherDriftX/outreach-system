"""Terminal table printer for each pipeline stage."""

from __future__ import annotations

import sys
from typing import Any


def print_discovery_summary(result: dict[str, Any]) -> None:
    signals = result.get("signals", [])
    per_adapter = result.get("per_adapter_rounds", {})
    novelty = result.get("per_adapter_novelty", {})

    print()
    _h1("STAGE 1: SIGNAL DISCOVERY")
    print(f"{'Adapter':<20s} {'Queries':>8s} {'Signals':>8s} {'Novelty':>8s}")
    print("-" * 48)
    for name in sorted(set(list(per_adapter) + list(novelty))):
        q = per_adapter.get(name, 0)
        n_hist = novelty.get(name, [])
        last_n = f"{n_hist[-1]:.0%}" if n_hist else "N/A"
        adapter_sigs = sum(1 for s in signals if s.get("source_name") == name)
        print(f"{name:<20s} {q:>8d} {adapter_sigs:>8d} {last_n:>8s}")

    triage_03 = sum(1 for s in signals if s.get("triage_score", 0) >= 1)
    print("-" * 48)
    print(f"Total signals: {len(signals)}")
    print(f"Qualified (score >= 1): {triage_03}")
    print(f"Score 0 (noise): {len(signals) - triage_03}")
    print()


def print_research_summary(leads: list[dict[str, Any]]) -> None:
    print()
    _h1("STAGE 2: LEAD RESEARCH")
    if not leads:
        print("No leads to research (no signals scored >= 1).")
        return

    print(f"{'Lead':<25s} {'Score':>5s} {'Facts':>5s} {'S':>3s} {'M':>3s} {'W':>3s}  Gap")
    print("-" * 80)
    for lead in leads:
        name = (lead.get("company_name") or lead.get("contact_name") or "Unknown")[:24]
        score = lead.get("triage_score", 0)
        s = lead.get("facts_strong", 0)
        m = lead.get("facts_moderate", 0)
        w = lead.get("facts_weak", 0)
        total = s + m + w
        gap = (lead.get("gap_hypothesis") or "")[:45]
        print(f"{name:<25s} {score:>5d} {total:>5d} {s:>3d} {m:>3d} {w:>3d}  {gap}")
    print("-" * 80)
    print(f"Total leads researched: {len(leads)}")
    print()


def print_craft_summary(leads: list[dict[str, Any]]) -> None:
    print()
    _h1("STAGE 3: OFFER CRAFTING")
    if not leads:
        print("No leads to build offers for.")
        return

    print(f"{'Lead':<25s} {'Subject':<35s} {'Unresolved':<25s}")
    print("-" * 88)
    for lead in leads:
        name = (lead.get("company_name") or lead.get("contact_name") or "Unknown")[:24]
        subject = (lead.get("offer_subject") or "")[:34]
        unresolved = (lead.get("unresolved") or "none")[:24]
        print(f"{name:<25s} {subject:<35s} {unresolved:<25s}")
    print("-" * 88)
    resolved = sum(1 for l in leads if not l.get("unresolved"))
    print(f"Fully resolved: {resolved}/{len(leads)}")
    print()


def _h1(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")