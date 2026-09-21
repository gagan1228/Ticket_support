# Support Ticket AI

An AI-powered system for querying and analysing customer support tickets using natural language. Built for the DOTMappers AI Engineer assessment.

---

## What it does

- **Natural language querying** — ask questions like *"Which agent has the lowest average rating?"* and get a plain-English answer backed by auto-generated SQL.
- **Anomaly detection** — automatically flags overdue high-priority tickets, outlier resolution times (IQR method), 1-star ratings, and suspiciously fast closes.
- **REST API** — three endpoints: `/query`, `/anomalies`, `/health` (plus `/stats` for the dashboard).
- **Streamlit UI** — a minimal dashboard covering all the above, plus an agent performance view.

---

## Architecture

```
support_tickets.csv
       │
       ▼
    db.py  ──── loads CSV into SQLite (tickets.db) on startup
       │
       ├── main.py  (FastAPI)
       │     ├── POST /query      ─── llm.py → Groq (NL→SQL) → SQLite → LLM summary
       │     ├── GET  /anomalies  ─── anomalies.py (rule + IQR based)
       │     ├── GET  /stats      ─── direct SQL aggregates
       │     └── GET  /health
       │
       └── app.py  (Streamlit)  ──── calls the FastAPI endpoints above
```

**LLM approach:** The user's question is sent to `qwen/qwen3.8-27b` on Groq with a schema description, and the model returns a raw SQLite query. That query runs against the local SQLite database. The result rows are sent back to the LLM a second time to get a plain-English summary. Two small calls, no embeddings, no vector store — keeps it simple and free.

---

## Setup

### 1. Clone & install

```bash
git clone <your-repo-url>
cd support-ticket-ai
pip install -r requirements.txt
```

### 2. Set your Groq API key

```bash
cp .env.example .env
# edit .env and paste your key from https://console.groq.com (free tier)
```

### 3. Run

```bash
python start.py
```

This starts both the API (port 8000) and the UI (port 8501) together.

Or run them separately:

```bash
# terminal 1
uvicorn main:app --reload

# terminal 2
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/query` | Natural language question → SQL → answer |
| GET | `/anomalies` | All detected anomalies with severity |
| GET | `/stats` | Ticket counts, ratings, agent breakdown |

### Example — `/query`

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many critical tickets are unresolved?"}'
```

```json
{
  "question": "How many critical tickets are unresolved?",
  "sql": "SELECT COUNT(*) FROM tickets WHERE priority = 'Critical' AND status != 'Resolved'",
  "answer": "There are 12 Critical tickets that are currently unresolved.",
  "row_count": 1,
  "data": [{"COUNT(*)": 12}]
}
```

---

## Example queries with outputs

**"How many tickets are currently open?"**
> There are currently 111 open tickets.

**"Which agent resolved the most tickets?"**
> AGT-12 resolved the most tickets with 37 resolutions.

**"Show me all Critical tickets not resolved within 12 hours."**
> Several Critical tickets exceeded 12hrs resolution time — the worst was TKT-255 handled by AGT-06 at 66.6hrs, followed by TKT-446 (AGT-04, 60.6hrs) and TKT-238 (AGT-12, 53.4hrs).

**"What is the average customer rating for Technical category tickets?"**
> The average customer rating for Technical tickets is 3.74 out of 5.

**"Which agent has the lowest average customer rating?"**
> AGT-08 has the lowest average customer rating at 3.48.

**"Are there any anomalies in resolution times this week?"**
> The `/anomalies` endpoint detected 35 anomalies total — 21 medium severity (slow resolutions via IQR), 14 low severity (1-star ratings).

---

## Model & tools used

| Component | Choice | Reason |
|-----------|--------|--------|
| LLM | `qwen/qwen3.8-27b` via Groq | Strong reasoning, good at SQL, free tier |
| Storage | SQLite | Zero-config, fits 500 rows fine, easy to query |
| Backend | FastAPI | Lightweight, auto-generates OpenAPI docs |
| UI | Streamlit | Quickest path to a working dashboard |

---

## Known limitations

- The NL→SQL step can misfire on ambiguous or multi-step questions (e.g. *"compare this week to last week"*). A retry loop or query planner would help.
- `resolution_time_hrs` is only populated for Resolved tickets — queries that mix it with Open tickets can return misleading results if the LLM doesn't account for NULLs.
- The system reconstructs `tickets.db` on every startup, so any runtime state (e.g. manual edits) is lost.
- No auth on the API — fine for local/assessment use, not for production.

---

## What I'd improve with more time

1. Add a query retry loop — if the generated SQL fails, send the error back to the LLM for a self-correction pass.
2. Persist the DB between restarts and add a `/reload` endpoint to refresh from CSV.
3. Stream the LLM response to the UI using Server-Sent Events.
4. Add more anomaly rules (e.g. agent suddenly drops in rating over a rolling window).
