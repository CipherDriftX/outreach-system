"""CLI entry point for Outreach OS.

Usage:
    python -m src.cli discover  [--limit N]
    python -m src.cli research  [--limit N]
    python -m src.cli craft
    python -m src.cli full      [--limit N]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline.discovery import discover
from src.pipeline.research import research_signals
from src.pipeline.craft import craft_offers, load_template
from src.pipeline.excel_writer import create_workbook
from src.pipeline.summary import (
    print_craft_summary,
    print_discovery_summary,
    print_research_summary,
)

_SIGNALS_CACHE: Path | None = None
_SIGNALS_DATA: list[dict] = []
_LEADS_DATA: list[dict] = []


def cmd_discover(args: argparse.Namespace) -> None:
    adapter_limit = args.adapters.split(",") if args.adapters else None
    result = discover(limit_adapters=adapter_limit)

    # Extract just triaged signals (score >= 1) for Excel
    triaged = [s for s in result["signals"] if s.get("triage_score", 0) >= 1]
    raw_all = result["signals"]

    print_discovery_summary(result)

    if not raw_all:
        print("No signals found. Try a broader query or check adapter connectivity.")
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"signals_{ts}.xlsx"
    path = create_workbook(raw_all, [], filename)

    global _SIGNALS_CACHE, _SIGNALS_DATA
    _SIGNALS_CACHE = path
    _SIGNALS_DATA = raw_all
    print(f"Written to {path}")


def cmd_research(args: argparse.Namespace) -> None:
    if not _SIGNALS_DATA:
        print("No signals in memory. Run 'discover' first, or pass --signals-file.")
        if args.signals_file:
            _load_signals_from_file(args.signals_file)
        else:
            return

    signals = _SIGNALS_DATA
    if args.limit:
        signals = signals[: args.limit]

    leads = research_signals(signals)
    print_research_summary(leads)

    if not leads:
        print("No leads to write.")
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"signals_{ts}.xlsx"
    path = create_workbook(signals, leads, filename)

    global _LEADS_DATA
    _LEADS_DATA = leads
    print(f"Written to {path}")


def cmd_craft(args: argparse.Namespace) -> None:
    if not _LEADS_DATA and not _SIGNALS_DATA:
        print("No leads in memory. Run 'research' first.")
        return

    template = load_template()
    if not template:
        print("No template found. Create config/template.txt with your offer structure.")
        return

    leads = craft_offers(_LEADS_DATA, _SIGNALS_DATA)
    print_craft_summary(leads)

    if not leads:
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"signals_{ts}.xlsx"
    path = create_workbook(_SIGNALS_DATA, leads, filename)
    print(f"Written to {path}")


def cmd_full(args: argparse.Namespace) -> None:
    adapter_limit = args.adapters.split(",") if args.adapters else None
    result = discover(limit_adapters=adapter_limit)
    print_discovery_summary(result)

    signals = result["signals"]
    qualified = [s for s in signals if s.get("triage_score", 0) >= 1]
    if args.limit:
        qualified = qualified[: args.limit]

    if not qualified:
        print("No qualified signals found. Outputting signals-only sheet.")
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = create_workbook(signals, [], f"signals_{ts}.xlsx")
        print(f"Written to {path}")
        return

    leads = research_signals(qualified)
    print_research_summary(leads)

    template = load_template()
    if template and leads:
        leads = craft_offers(leads, signals)
        print_craft_summary(leads)
    elif not template:
        print("  No template found. Create config/template.txt for offer generation.")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = create_workbook(signals, leads, f"signals_{ts}.xlsx")
    print(f"Written to {path}")


def _load_signals_from_file(filepath: str) -> None:
    import pandas as pd

    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return
    df = pd.read_excel(path, sheet_name="Signals")
    global _SIGNALS_DATA
    _SIGNALS_DATA = df.to_dict("records")


def main() -> None:
    parser = argparse.ArgumentParser(description="Outreach OS — signal to offer pipeline")
    sub = parser.add_subparsers(dest="command")

    d = sub.add_parser("discover", help="Find signals")
    d.add_argument("--adapters", type=str, help="Comma-separated adapter names")
    d.add_argument("--limit", type=int, help="Limit discovery rounds")

    r = sub.add_parser("research", help="Research leads from signals")
    r.add_argument("--signals-file", type=str, help="Path to signals Excel file")
    r.add_argument("--limit", type=int, default=5, help="Max leads to research")

    sub.add_parser("craft", help="Build offers from researched leads")

    f = sub.add_parser("full", help="Run all three stages")
    f.add_argument("--adapters", type=str, help="Comma-separated adapter names")
    f.add_argument("--limit", type=int, default=3, help="Max leads to research and craft")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "discover":
        cmd_discover(args)
    elif args.command == "research":
        cmd_research(args)
    elif args.command == "craft":
        cmd_craft(args)
    elif args.command == "full":
        cmd_full(args)


if __name__ == "__main__":
    main()