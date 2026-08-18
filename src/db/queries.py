"""Common database queries for Outreach OS."""

from __future__ import annotations

from src.db.connection import get_connection, put_connection


def ping() -> bool:
    conn = get_connection(timeout=2.0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return True
    finally:
        put_connection(conn)


def get_business_id() -> str | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM businesses LIMIT 1")
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    finally:
        put_connection(conn)


def get_leads_by_status(status: str) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT l.id, l.company_name, l.contact_name, l.contact_email,
                      l.status, l.signal_strength_score, l.origin_signal_id,
                      l.created_at, s.raw_text, s.source_type, s.source_name, s.url
               FROM leads l JOIN signals s ON l.origin_signal_id = s.id
               WHERE l.status = %s ORDER BY l.created_at DESC""",
            [status],
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "company_name": r[1],
                "contact_name": r[2],
                "contact_email": r[3],
                "status": r[4],
                "signal_strength_score": r[5],
                "origin_signal_id": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
                "signal_raw_text": r[8],
                "signal_source_type": r[9],
                "signal_source_name": r[10],
                "signal_url": r[11],
            }
            for r in rows
        ]
    finally:
        put_connection(conn)


def get_lead_facts(lead_id: str) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, fact_type, track, fact, source_url, observed_at,
                      corroboration_count, consistency, recency_days,
                      effect_size, grade
               FROM lead_facts WHERE lead_id = %s ORDER BY grade, fact_type""",
            [lead_id],
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "fact_type": r[1],
                "track": r[2],
                "fact": r[3],
                "source_url": r[4],
                "observed_at": r[5].isoformat() if r[5] else None,
                "corroboration_count": r[6],
                "consistency": float(r[7]) if r[7] else None,
                "recency_days": r[8],
                "effect_size": float(r[9]) if r[9] else None,
                "grade": r[10],
            }
            for r in rows
        ]
    finally:
        put_connection(conn)


def get_gap_hypothesis(lead_id: str) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, fact, grade, source_url, corroboration_count
               FROM lead_facts
               WHERE lead_id = %s AND fact_type = 'gap_hypothesis'
               LIMIT 1""",
            [lead_id],
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return {
            "id": row[0],
            "fact": row[1],
            "grade": row[2],
            "source_url": row[3],
            "corroboration_count": row[4],
        }
    finally:
        put_connection(conn)


def get_signals(business_id: str, limit: int = 100) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT s.id, s.source_type, s.source_name, s.url,
                      s.author_handle, s.raw_text, s.matched_pattern,
                      s.posted_at, s.captured_at,
                      l.id as lead_id, l.status as lead_status
               FROM signals s
               LEFT JOIN leads l ON l.origin_signal_id = s.id
               WHERE s.business_id = %s
               ORDER BY s.captured_at DESC LIMIT %s""",
            [business_id, limit],
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "source_type": r[1],
                "source_name": r[2],
                "url": r[3],
                "author_handle": r[4],
                "raw_text": r[5],
                "matched_pattern": r[6],
                "posted_at": r[7].isoformat() if r[7] else None,
                "captured_at": r[8].isoformat() if r[8] else None,
                "lead_id": r[9],
                "lead_status": r[10],
            }
            for r in rows
        ]
    finally:
        put_connection(conn)


def get_active_template(business_id: str) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, name, template_text, updated_at
               FROM offer_templates
               WHERE business_id = %s AND is_active = true
               ORDER BY updated_at DESC LIMIT 1""",
            [business_id],
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "template_text": row[2],
            "updated_at": row[3].isoformat() if row[3] else None,
        }
    finally:
        put_connection(conn)


def upsert_template(business_id: str, template_text: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO offer_templates (business_id, name, template_text, is_active, updated_at)
               VALUES (%s, 'default', %s, true, now())
               ON CONFLICT DO NOTHING""",
            [business_id, template_text],
        )
        cur.execute(
            """UPDATE offer_templates
               SET template_text = %s, updated_at = now()
               WHERE business_id = %s AND is_active = true""",
            [template_text, business_id],
        )
        conn.commit()
        cur.close()
        return get_active_template(business_id) or {}
    except Exception:
        conn.rollback()
        raise
    finally:
        put_connection(conn)


def get_pipeline_stats(business_id: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT status, count(*) FROM leads
               WHERE business_id = %s GROUP BY status""",
            [business_id],
        )
        rows = cur.fetchall()
        cur.close()
        stats = {r[0]: r[1] for r in rows}
        return {
            "found": stats.get("found", 0),
            "researching": stats.get("researching", 0),
            "researched": stats.get("researched", 0),
            "offer_drafted": stats.get("offer_drafted", 0),
            "offer_approved": stats.get("offer_approved", 0),
            "total_signals": _count(conn, "signals", business_id),
            "total_leads": sum(stats.values()),
        }
    finally:
        put_connection(conn)


def _count(conn, table: str, business_id: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT count(*) FROM {table} WHERE business_id = %s", [business_id])
    row = cur.fetchone()
    cur.close()
    return row[0] if row else 0