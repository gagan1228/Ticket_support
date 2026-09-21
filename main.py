from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from db import init_db, run_query, get_conn
from llm import nl_to_sql, summarize_results
from anomalies import detect_anomalies


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Support Ticket AI",
    description="Natural language querying and anomaly detection over customer support tickets.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


# ── endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "support-ticket-ai"}


@app.post("/query")
def query(req: QueryRequest):
    """
    Accepts a plain-English question and returns:
    - the generated SQL
    - a natural-language answer from the LLM
    - raw result rows (up to 100)
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        sql = nl_to_sql(req.question)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    try:
        rows, columns = run_query(sql)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Generated SQL failed to execute: {e}\nSQL: {sql}",
        )

    answer = summarize_results(req.question, sql, rows, columns)

    return {
        "question": req.question,
        "sql": sql,
        "answer": answer,
        "row_count": len(rows),
        "columns": columns,
        "data": [dict(zip(columns, r)) for r in rows[:100]],
    }


@app.get("/anomalies")
def anomalies():
    """
    Runs all anomaly detection rules against the loaded ticket data.
    Returns flagged tickets grouped by severity.
    """
    try:
        results = detect_anomalies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    high   = [a for a in results if a["severity"] == "high"]
    medium = [a for a in results if a["severity"] == "medium"]
    low    = [a for a in results if a["severity"] == "low"]

    return {
        "total": len(results),
        "summary": {"high": len(high), "medium": len(medium), "low": len(low)},
        "anomalies": results,
    }


@app.get("/stats")
def stats():
    """
    Returns a quick overview of the dataset — useful for the dashboard sidebar.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tickets")
    total = cur.fetchone()[0]

    cur.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status ORDER BY COUNT(*) DESC")
    by_status = dict(cur.fetchall())

    cur.execute("SELECT priority, COUNT(*) FROM tickets GROUP BY priority ORDER BY COUNT(*) DESC")
    by_priority = dict(cur.fetchall())

    cur.execute("SELECT category, COUNT(*) FROM tickets GROUP BY category ORDER BY COUNT(*) DESC")
    by_category = dict(cur.fetchall())

    cur.execute("SELECT ROUND(AVG(customer_rating), 2) FROM tickets WHERE customer_rating IS NOT NULL")
    avg_rating = cur.fetchone()[0]

    cur.execute("""
        SELECT
            agent_id,
            COUNT(*) AS resolved_count,
            ROUND(AVG(customer_rating), 2) AS avg_rating,
            ROUND(AVG(resolution_time_hrs), 2) AS avg_resolution_hrs
        FROM tickets
        WHERE status = 'Resolved'
        GROUP BY agent_id
        ORDER BY resolved_count DESC
    """)
    cols = ["agent_id", "resolved_count", "avg_rating", "avg_resolution_hrs"]
    agents = [dict(zip(cols, r)) for r in cur.fetchall()]

    conn.close()

    return {
        "total_tickets": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "avg_customer_rating": avg_rating,
        "agent_performance": agents,
    }
