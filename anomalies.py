import statistics
from db import get_conn


def detect_anomalies() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    found = []

    # --- Rule 1: Critical or High tickets still open/escalated ---
    # anything unresolved after 24hrs of response time is a red flag
    cur.execute("""
        SELECT ticket_id, priority, status, created_at, response_time_hrs
        FROM tickets
        WHERE status IN ('Open', 'Escalated')
          AND priority IN ('Critical', 'High')
          AND response_time_hrs > 24
    """)
    for ticket_id, priority, status, created_at, rt in cur.fetchall():
        found.append({
            "ticket_id": ticket_id,
            "anomaly_type": "overdue_high_priority",
            "description": f"{priority} priority ticket is still {status} after {rt}hrs response time (created {created_at})",
            "severity": "high",
        })

    # --- Rule 2: IQR-based outliers on resolution time ---
    cur.execute("""
        SELECT ticket_id, resolution_time_hrs
        FROM tickets
        WHERE resolution_time_hrs IS NOT NULL
    """)
    resolved = cur.fetchall()
    times = [r[1] for r in resolved]

    if len(times) >= 10:
        q1 = statistics.quantiles(times, n=4)[0]
        q3 = statistics.quantiles(times, n=4)[2]
        iqr = q3 - q1
        upper = q3 + 1.5 * iqr

        for ticket_id, t in resolved:
            if t > upper:
                found.append({
                    "ticket_id": ticket_id,
                    "anomaly_type": "slow_resolution",
                    "description": f"Resolution took {round(t, 1)}hrs — well above the {round(upper, 1)}hr threshold (IQR method)",
                    "severity": "medium",
                })

    cur.execute("""
        SELECT ticket_id, agent_id, category, customer_rating
        FROM tickets
        WHERE customer_rating = 1
          AND status = 'Resolved'
    """)
    for ticket_id, agent_id, category, rating in cur.fetchall():
        found.append({
            "ticket_id": ticket_id,
            "anomaly_type": "poor_customer_rating",
            "description": f"Agent {agent_id} got a 1-star rating on a {category} ticket",
            "severity": "low",
        })

   
    cur.execute("""
        SELECT ticket_id, agent_id, resolution_time_hrs, priority
        FROM tickets
        WHERE resolution_time_hrs < 0.1
          AND status = 'Resolved'
    """)
    for ticket_id, agent_id, t, priority in cur.fetchall():
        found.append({
            "ticket_id": ticket_id,
            "anomaly_type": "suspiciously_fast_resolution",
            "description": f"Ticket resolved in {round(t * 60, 1)} minutes by {agent_id} — possible premature close ({priority} priority)",
            "severity": "medium",
        })

    conn.close()
    return found
