"""CLI entry point for Outreach OS.

Usage:
    python -m src.cli discover  [--adapters X,Y]
    python -m src.cli research  [--limit N]
    python -m src.cli craft
    python -m src.cli full      [--limit N]  [--adapters X,Y]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline.discovery import discover as run_discovery
from src.pipeline.research import research_signals as run_research
from src.pipeline.craft import craft_offers as run_craft, load_template
from src.pipeline.excel_writer import create_workbook
from src.pipeline.summary import (
    print_discovery_summary,
    print_research_summary,
    print_craft_summary,
)

_SIGNALS: list[dict] = []
_LEADS: list[dict] = []


def cmd_discover(args: argparse.Namespace) -> None:
    adapter_list = args.adapters.split(",") if args.adapters else None
    result = run_discovery(limit_adapters=adapter_list)
    signals = result.get("signals", [])
    leads = result.get("leads", [])

    print_discovery_summary(result)

    global _SIGNALS, _LEADS
    _SIGNALS = signals
    _LEADS = leads

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = create_workbook(signals, [], f"signals_{ts}.xlsx")
    print(f"Written to {path}")


def cmd_research(args: argparse.Namespace) -> None:
    leads = _LEADS
    if args.signals_file:
        import pandas as pd
        df = pd.read_excel(args.signals_file, sheet_name="Signals")
        signals = df.to_dict("records")
        global _SIGNALS
        _SIGNALS = signals
        qualified = [s for s in signals if s.get("triage_score", 0) >= 1]
        leads = [
            {"lead_id": f"l{i}", "signal_id": s.get("signal_id", ""),
             "triage_score": s.get("triage_score", 0),
             "signal": s,
             "company_name": s.get("author_handle", ""),
             "contact_name": s.get("author_handle", "")}
            for i, s in enumerate(qualified)
        ]

    if not leads:
        print("No leads in memory. Run 'discover' first, or pass --signals-file.")
        return

    if args.limit:
        leads = leads[:args.limit]

    results = run_research(leads)
    print_research_summary(results)

    _LEADS = results
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = create_workbook(_SIGNALS, results, f"signals_{ts}.xlsx")
    print(f"Written to {path}")


def cmd_craft(args: argparse.Namespace) -> None:
    if not _LEADS and not _SIGNALS:
        print("No leads in memory. Run 'research' first.")
        return

    template = load_template()
    if not template:
        print("No template found. Create config/template.txt with your offer structure.")
        return

    leads = run_craft(_LEADS, _SIGNALS)
    print_craft_summary(leads)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = create_workbook(_SIGNALS, leads, f"signals_{ts}.xlsx")
    print(f"Written to {path}")


def cmd_full(args: argparse.Namespace) -> None:
    from src.config import get_config
    if not get_config().openrouter.api_key:
        print("OPENROUTER_API_KEY not set in .env. Deep research requires an LLM.")
        print("Set it and re-run for multi-layer recursive depth.")
        return

    adapter_list = args.adapters.split(",") if args.adapters else None
    result = run_discovery(limit_adapters=adapter_list)
    print_discovery_summary(result)

    signals = result.get("signals", [])
    leads = result.get("leads", [])

    global _SIGNALS, _LEADS
    _SIGNALS = signals
    _LEADS = leads

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if not leads:
        print("No qualified leads found. Outputting signals-only sheet.")
        path = create_workbook(signals, [], f"signals_{ts}.xlsx")
        print(f"Written to {path}")
        return

    if args.limit:
        leads = leads[:args.limit]

    print(f"\nResearching {len(leads)} leads...")
    researched = run_research(leads)
    print_research_summary(researched)

    template = load_template()
    if template and researched:
        crafted = run_craft(researched, signals)
        print_craft_summary(crafted)
    else:
        crafted = researched
        if not template:
            print("  No template found. Create config/template.txt.")

    path = create_workbook(signals, crafted, f"signals_{ts}.xlsx")
    print(f"\nWritten to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Outreach OS — recursive graph research pipeline")
    sub = parser.add_subparsers(dest="command")

    d = sub.add_parser("discover", help="Find signals via recursive graph")
    d.add_argument("--adapters", type=str)

    r = sub.add_parser("research", help="Deep research on leads")
    r.add_argument("--signals-file", type=str)
    r.add_argument("--limit", type=int, default=3)

    sub.add_parser("craft", help="Build offers from researched leads")

    f = sub.add_parser("full", help="All three stages")
    f.add_argument("--adapters", type=str)
    f.add_argument("--limit", type=int, default=2)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmd_map = {"discover": cmd_discover, "research": cmd_research, "craft": cmd_craft, "full": cmd_full}
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()