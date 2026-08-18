# Outreach OS — Plarix

Autonomous email outreach system. A recursive research graph finds signals
anywhere on the internet, researches each signal into a hyper-personalized
lead dossier, and fills your offer template with graded, sourced facts.

**No LLM writes your email.** The template engine fills `[fact_fields]` and
`(signal_fields)` from researched facts only. Missing or weak facts are
omitted — never invented.

## Architecture

```
Node 1 — SIGNAL    LangGraph discovery graph: ICP taxonomy → dual-track
                   (intent queries + lookalike walk) → frontier/saturation
                   → split detection → 0-3 triage → leads with
                   origin_signal_id (NOT NULL, enforced in schema)

Node 2 — RESEARCH  Per-lead subgraph: enrichment (Track A) + relationship
                   walk (Track B) → compaction → four-axis evidence grading
                   (corroboration/consistency/recency/effect size)
                   → gap hypothesis tracing to the origin signal

Node 3 — CRAFT     Deterministic template engine: your template text,
                   [fact]/(signal)/[if] placeholders, grade-gated rendering

Node 4 — SEND      Deferred (v1 is research + offer building only)
```

## Setup

```bash
# 1. Database
docker compose up -d                    # Postgres on :5432

# 2. Backend
python -m pip install -e '.[dev]'
cp .env.example .env                    # fill in OPENROUTER_API_KEY + source API keys

# 3. Frontend
cd web && npm install && npm run build && cd ..

# 4. Run
uvicorn src.api.server:app --port 8000  # UI at http://localhost:8000
```

Frontend dev mode (two servers):

```bash
uvicorn src.api.server:app --reload --port 8000
cd web && npm run dev                   # http://localhost:5173
```

## Usage

1. **Dashboard → "Start Signal Discovery"** — the graph builds the ICP
   taxonomy, searches all adapters (Reddit, HN, X, Stack Exchange, Upwork,
   GitHub, Bluesky), saturates each source, and triages signals into leads.
2. **"Research Leads"** — each triaged lead gets a deep multi-dimensional
   research pass: company basics, contact, pains, tech stack, competitors,
   recent activity, social graph. Every fact graded strong/moderate/weak.
3. **Offers → Template** — write your offer structure with
   `[gap_hypothesis_summary]`, `(signal_raw_text_snippet)`,
   `[if tech_stack: any]…[/if]`. Saved to the database; persists.
4. **"Generate Offers"** — the template engine fills each placeholder from
   that lead's graded facts. Unresolved placeholders are omitted, not guessed.

## API keys

- `OPENROUTER_API_KEY` — required (DeepSeek V4-Pro/Flash, Kimi fallback)
- `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` — optional, raises rate limit
- `TWITTER_BEARER_TOKEN` — optional, enables X search
- `GITHUB_TOKEN` — optional, raises GitHub rate limit
- `STACKEXCHANGE_KEY` — optional

## Test

```bash
python -m pytest tests/ -q   # 28 tests, all deterministic, zero API calls
```
