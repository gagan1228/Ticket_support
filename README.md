# Support Ticket AI

An AI-powered system for querying and analysing customer support tickets using natural language. 

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


## Model & tools used

| Component | Choice | Reason |
|-----------|--------|--------|
| LLM | `qwen/qwen3.8-27b` via Groq | Strong reasoning, good at SQL, free tier |
| Storage | SQLite | Zero-config, fits 500 rows fine, easy to query |
| Backend | FastAPI | Lightweight, auto-generates OpenAPI docs |
| UI | Streamlit | Quickest path to a working dashboard |

