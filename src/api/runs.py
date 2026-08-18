"""Runs API — launch signal discovery runs, track their status.

Runs execute the Node 1 discovery graph in a background thread. The UI polls
run status from the JSONL log sink and the structured store.
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.queries import get_business_id

router = APIRouter(tags=["runs"])

_RUNS: dict[str, dict[str, Any]] = {}
_RUN_LOCK = threading.Lock()


class RunRequest(BaseModel):
    icp_root: str | None = None


@router.get("/runs")
def api_list_runs() -> list[dict[str, Any]]:
    with _RUN_LOCK:
        return sorted(
            [_RUNS[r] for r in _RUNS],
            key=lambda r: r.get("started_at", ""),
            reverse=True,
        )


@router.post("/runs", status_code=201)
def api_launch_run(req: RunRequest) -> dict[str, Any]:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")

    run_id = str(uuid.uuid4())
    thread_id = f"signal-run-{run_id}"

    with _RUN_LOCK:
        _RUNS[run_id] = {
            "run_id": run_id,
            "thread_id": thread_id,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "phase": "starting",
            "error": None,
        }

    threading.Thread(
        target=_run_signal_discovery_bg,
        args=(business_id, run_id, thread_id, req.icp_root),
        daemon=True,
    ).start()

    return {"run_id": run_id, "thread_id": thread_id, "status": "running"}


@router.get("/runs/{run_id}")
def api_get_run(run_id: str) -> dict[str, Any]:
    with _RUN_LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Unknown run: {run_id}")
        return dict(run)


@router.get("/runs/{run_id}/logs")
def api_run_logs(run_id: str, since: int = 0) -> dict[str, Any]:
    path = Path("logs") / f"run_{run_id}.jsonl"
    if not path.exists():
        return {"entries": [], "cursor": since}

    entries = []
    with open(path) as f:
        lines = f.readlines()[since:]
        for line in lines:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {"entries": entries, "cursor": since + len(lines)}


def _run_signal_discovery_bg(
    business_id: str, run_id: str, thread_id: str, icp_root: str | None
) -> None:
    try:
        from src.db.connection import get_connection, put_connection
        from src.nodes.signal.taxonomy import build_taxonomy
        from src.observability.logs import write_node_logs

        # Load ICP taxonomy from store, or build it via LLM
        taxonomy = _load_taxonomy(business_id)
        if not taxonomy or not taxonomy.get("verticals"):
            root = icp_root or _load_icp_root(business_id) or (
                "Businesses with painful operational processes that are candidates for autonomous AI execution"
            )
            with _RUN_LOCK:
                _RUNS[run_id]["phase"] = "building_taxonomy"
            write_node_logs(
                run_id,
                [
                    {
                        "node_name": "build_taxonomy",
                        "input_summary": {"icp_root": root[:100]},
                    }
                ],
            )
            taxonomy = build_taxonomy(root, business_id)
            _persist_taxonomy(business_id, taxonomy)

        asyncio.run(_run_graph(business_id, run_id, thread_id, taxonomy))
    except Exception as exc:
        with _RUN_LOCK:
            _RUNS[run_id]["status"] = "failed"
            _RUNS[run_id]["error"] = str(exc)
            _RUNS[run_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


async def _run_graph(business_id: str, run_id: str, thread_id: str, taxonomy: dict) -> None:
    from src.db.checkpointer import get_async_checkpointer
    from src.graph import run_signal_discovery

    checkpointer = await get_async_checkpointer()
    try:
        final = await run_signal_discovery(
            business_id=business_id,
            run_id=run_id,
            thread_id=thread_id,
            taxonomy=taxonomy,
            checkpointer=checkpointer,
        )
        with _RUN_LOCK:
            _RUNS[run_id]["status"] = "completed"
            _RUNS[run_id]["phase"] = final.get("current_phase", "done")
            _RUNS[run_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
            _RUNS[run_id]["summary"] = {
                "signals_discovered": len(final.get("discovered_signal_ids", [])),
                "leads_created": len(final.get("discovered_lead_ids", [])),
                "errors": len(final.get("errors", [])),
            }
    except Exception as exc:
        with _RUN_LOCK:
            _RUNS[run_id]["status"] = "failed"
            _RUNS[run_id]["error"] = str(exc)
            _RUNS[run_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


def _load_taxonomy(business_id: str) -> dict:
    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT icp_taxonomy FROM businesses WHERE id = %s", [business_id]
        )
        row = cur.fetchone()
        cur.close()
        if row and row[0]:
            data = row[0]
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    data = {}
            return data
        return {}
    finally:
        put_connection(conn)


def _persist_taxonomy(business_id: str, taxonomy: dict) -> None:
    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE businesses SET icp_taxonomy = %s WHERE id = %s",
            [json.dumps(taxonomy), business_id],
        )
        conn.commit()
        cur.close()
    finally:
        put_connection(conn)


def _load_icp_root(business_id: str) -> str:
    taxonomy = _load_taxonomy(business_id)
    return taxonomy.get("root", "")