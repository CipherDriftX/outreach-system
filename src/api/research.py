"""Research run — processes leads in 'found' status through Node 2.

Each lead gets its own research subgraph instance. Fanned out via threading
(can be upgraded to LangGraph Send when the master graph is built).

This is the operational entrypoint: after Node 1 finds and triages signals,
Node 2 researches each lead independently and in parallel.
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from src.db.queries import get_business_id, get_leads_by_status

router = APIRouter(tags=["research"])

_RESEARCH_JOBS: dict[str, dict[str, Any]] = {}
_JOB_LOCK = threading.Lock()


@router.post("/research/run", status_code=201)
def api_run_research() -> dict[str, Any]:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")

    leads = get_leads_by_status("found")
    if not leads:
        return {"status": "no_leads", "message": "No leads in 'found' status to research"}

    job_id = str(uuid4())

    with _JOB_LOCK:
        _RESEARCH_JOBS[job_id] = {
            "job_id": job_id,
            "status": "running",
            "total": len(leads),
            "completed": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "lead_ids": [l["id"] for l in leads],
        }

    threading.Thread(
        target=_run_research_bg,
        args=(business_id, job_id, leads),
        daemon=True,
    ).start()

    return {"job_id": job_id, "total": len(leads), "status": "running"}


@router.get("/research/jobs/{job_id}")
def api_get_research_job(job_id: str) -> dict[str, Any]:
    with _JOB_LOCK:
        job = _RESEARCH_JOBS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
        return dict(job)


@router.post("/research/lead/{lead_id}")
def api_research_single_lead(lead_id: str) -> dict[str, Any]:
    business_id = get_business_id()
    if not business_id:
        raise HTTPException(status_code=404, detail="No business configured")

    try:
        asyncio.run(_research_one_lead(business_id, lead_id))
        return {"status": "completed", "lead_id": lead_id}
    except Exception as exc:
        return {"status": "failed", "lead_id": lead_id, "error": str(exc)}


def _run_research_bg(business_id: str, job_id: str, leads: list[dict]) -> None:
    try:
        for i, lead in enumerate(leads):
            try:
                asyncio.run(_research_one_lead(business_id, lead["id"]))
            except Exception:
                pass
            with _JOB_LOCK:
                _RESEARCH_JOBS[job_id]["completed"] = i + 1
        with _JOB_LOCK:
            _RESEARCH_JOBS[job_id]["status"] = "completed"
            _RESEARCH_JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        with _JOB_LOCK:
            _RESEARCH_JOBS[job_id]["status"] = "failed"
            _RESEARCH_JOBS[job_id]["error"] = str(exc)


async def _research_one_lead(business_id: str, lead_id: str) -> dict:
    from src.db.checkpointer import get_async_checkpointer
    from src.nodes.research.graph import compile_lead_graph

    checkpointer = await get_async_checkpointer()
    graph = compile_lead_graph(checkpointer=checkpointer)

    initial = {
        "lead_id": lead_id,
        "business_id": business_id,
    }

    config = {
        "configurable": {"thread_id": f"research-lead-{lead_id}"},
        "recursion_limit": 50,
    }

    final = await graph.ainvoke(initial, config=config)
    return final