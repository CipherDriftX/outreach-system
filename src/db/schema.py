"""Full schema DDL for Outreach OS.

Tables: businesses, signal_sources, signals, leads, lead_facts,
relationship_edges, offer_templates, offers.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    icp_taxonomy JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    adapter TEXT NOT NULL,
    track CHAR(1) NOT NULL CHECK (track IN ('A','B')),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    budget_share NUMERIC,
    last_saturated_at TIMESTAMPTZ,
    schema_version INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    signal_source_id UUID REFERENCES signal_sources(id),
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    url TEXT NOT NULL,
    author_handle TEXT,
    raw_text TEXT NOT NULL,
    matched_pattern TEXT,
    posted_at TIMESTAMPTZ,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    schema_version INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    company_name TEXT,
    contact_name TEXT,
    contact_email TEXT,
    status TEXT NOT NULL DEFAULT 'found',
    signal_strength_score SMALLINT,
    origin_signal_id UUID NOT NULL REFERENCES signals(id),
    dedup_key TEXT NOT NULL UNIQUE,
    schema_version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lead_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id),
    fact_type TEXT NOT NULL DEFAULT 'observation',
    track CHAR(1) NOT NULL CHECK (track IN ('A','B')),
    fact TEXT NOT NULL,
    source_url TEXT,
    observed_at TIMESTAMPTZ,
    corroboration_count SMALLINT DEFAULT 1,
    consistency NUMERIC,
    recency_days INT,
    effect_size NUMERIC,
    grade TEXT CHECK (grade IN ('strong','moderate','weak')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS relationship_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    relation TEXT NOT NULL,
    weight NUMERIC NOT NULL DEFAULT 1.0,
    source_url TEXT,
    observed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS offer_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    name TEXT NOT NULL DEFAULT 'default',
    template_text TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_offer_templates_active
    ON offer_templates(business_id) WHERE is_active;

CREATE TABLE IF NOT EXISTS offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id),
    template_id UUID REFERENCES offer_templates(id),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    resolved_fact_ids UUID[] NOT NULL DEFAULT '{}',
    unresolved_placeholders TEXT[] NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signals_business ON signals(business_id);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(signal_source_id);
CREATE INDEX IF NOT EXISTS idx_leads_business ON leads(business_id);
CREATE INDEX IF NOT EXISTS idx_leads_origin_signal ON leads(origin_signal_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_lead_facts_lead ON lead_facts(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_facts_type ON lead_facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_relationship_edges_from ON relationship_edges(from_entity);
CREATE INDEX IF NOT EXISTS idx_relationship_edges_to ON relationship_edges(to_entity);
CREATE INDEX IF NOT EXISTS idx_offers_lead ON offers(lead_id);
"""

SEED = """
INSERT INTO businesses (id, name, icp_taxonomy)
VALUES (
    gen_random_uuid(),
    'Plarix',
    '{"root": "Businesses with painful operational processes that are candidates for autonomous AI execution", "verticals": []}'::jsonb
)
ON CONFLICT DO NOTHING;
"""


def _get_default_template() -> str:
    try:
        import yaml
        from pathlib import Path
        path = Path(__file__).resolve().parents[2] / "config" / "governors.yaml"
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
                return data.get("craft", {}).get("default_template", "")
    except Exception:
        pass
    return ""


def create_schema(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute(DDL)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def seed_defaults(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute(SEED)
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close()

    template = _get_default_template()
    if template:
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO offer_templates (business_id, name, template_text, is_active)
                   SELECT id, 'default', %s, true FROM businesses LIMIT 1
                   ON CONFLICT (business_id) WHERE is_active DO NOTHING""",
                [template],
            )
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            cur.close()


def ensure_schema() -> None:
    from src.db.connection import get_connection, put_connection

    conn = get_connection()
    try:
        create_schema(conn)
        seed_defaults(conn)
    finally:
        put_connection(conn)


def drop_schema(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute("DROP TABLE IF EXISTS offers CASCADE")
        cur.execute("DROP TABLE IF EXISTS offer_templates CASCADE")
        cur.execute("DROP TABLE IF EXISTS relationship_edges CASCADE")
        cur.execute("DROP TABLE IF EXISTS lead_facts CASCADE")
        cur.execute("DROP TABLE IF EXISTS leads CASCADE")
        cur.execute("DROP TABLE IF EXISTS signals CASCADE")
        cur.execute("DROP TABLE IF EXISTS signal_sources CASCADE")
        cur.execute("DROP TABLE IF EXISTS businesses CASCADE")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()