import sqlite3
import csv
import os

DB_PATH = "tickets.db"
CSV_PATH = "support_tickets.csv"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    # wipe and rebuild on every startup so data stays fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE tickets (
            ticket_id           TEXT PRIMARY KEY,
            created_at          TEXT,
            category            TEXT,
            priority            TEXT,
            status              TEXT,
            response_time_hrs   REAL,
            resolution_time_hrs REAL,
            agent_id            TEXT,
            customer_rating     REAL,
            issue_summary       TEXT
        )
    """)

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append((
                row["ticket_id"],
                row["created_at"],
                row["category"],
                row["priority"],
                row["status"],
                float(row["response_time_hrs"]) if row["response_time_hrs"].strip() else None,
                float(row["resolution_time_hrs"]) if row["resolution_time_hrs"].strip() else None,
                row["agent_id"],
                float(row["customer_rating"]) if row["customer_rating"].strip() else None,
                row["issue_summary"],
            ))

    cur.executemany("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    print(f"[db] loaded {len(rows)} tickets into SQLite")


def run_query(sql: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return rows, columns
