import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "qwen/qwen3.8-27b"

# describes the tickets table so the LLM knows what it's working with
SCHEMA_DESC = """
Table name: tickets

Columns:
  ticket_id           TEXT    — unique ID like "TKT-001"
  created_at          TEXT    — datetime string, e.g. "2024-02-05 11:14"
  category            TEXT    — one of: Billing, Technical, General
  priority            TEXT    — one of: Critical, High, Medium, Low
  status              TEXT    — one of: Open, Resolved, Escalated
  response_time_hrs   REAL    — hours to first response (can be NULL)
  resolution_time_hrs REAL    — hours to resolve; NULL if not yet resolved
  agent_id            TEXT    — agent identifier like "AGT-03"
  customer_rating     REAL    — rating from 1 to 5; NULL if not yet rated
  issue_summary       TEXT    — short description of the issue
"""


def nl_to_sql(question: str) -> str:
    prompt = f"""You are a SQLite query expert. Convert the user question into a valid SQLite SELECT query.

{SCHEMA_DESC}

Important rules:
- Return ONLY the raw SQL query. No markdown, no explanation, no backticks.
- Use strftime() for any date/time operations on the created_at column.
- resolution_time_hrs and customer_rating are NULL for unresolved tickets — account for this in filters.
- Do not use LIMIT unless the user specifically asks for a limited number of results.
- If the question cannot be answered with SQL, return: SELECT 'Unable to process this query' AS message

User question: {question}
SQL:"""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=400,
    )

    raw = resp.choices[0].message.content.strip()

    # strip markdown code fences if the model adds them anyway
    raw = re.sub(r"```[\w]*", "", raw).strip("`").strip()

    return raw


def summarize_results(question: str, sql: str, rows: list, columns: list) -> str:
    if not rows:
        return "No results found for that query."

    # only send up to 30 rows to keep prompt size reasonable
    sample = rows[:30]
    rows_text = "\n".join(str(dict(zip(columns, r))) for r in sample)
    note = f"(showing {len(sample)} of {len(rows)} rows)" if len(rows) > 30 else ""

    prompt = f"""You are a concise data analyst. Given the user's question, the SQL that was run, and the results, write a short, clear answer.

Question: {question}
SQL: {sql}
Results {note}:
{rows_text}

Write a direct 1-3 sentence answer. Lead with the key number or fact. Do not repeat the question."""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=250,
    )

    return resp.choices[0].message.content.strip()
