import streamlit as st
import requests
import pandas as pd

API = "http://localhost:8000"

st.set_page_config(
    page_title="Support Ticket AI",
    page_icon="🎫",
    layout="wide",
)

st.title("🎫 Support Ticket AI Dashboard")
st.caption("Natural language querying + anomaly detection over 500 support tickets")


def api_get(path):
    try:
        r = requests.get(f"{API}{path}", timeout=10)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach the API. Make sure the FastAPI server is running on port 8000."
    except Exception as e:
        return None, str(e)


def api_post(path, body):
    try:
        r = requests.post(f"{API}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach the API."
    except Exception as e:
        return None, str(e)


# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📊 Overview")
    stats, err = api_get("/stats")

    if err:
        st.error(err)
    else:
        col1, col2 = st.columns(2)
        col1.metric("Total Tickets", stats["total_tickets"])
        col2.metric("Avg Rating", f"⭐ {stats['avg_customer_rating']}")

        st.divider()
        st.subheader("By Status")
        for status, count in stats["by_status"].items():
            bar = "█" * int(count / stats["total_tickets"] * 20)
            st.write(f"**{status}** — {count}  `{bar}`")

        st.divider()
        st.subheader("By Priority")
        priority_colors = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
        for p, count in stats["by_priority"].items():
            icon = priority_colors.get(p, "⚪")
            st.write(f"{icon} **{p}**: {count}")

        st.divider()
        st.subheader("By Category")
        for cat, count in stats["by_category"].items():
            st.write(f"**{cat}**: {count}")


# ── main tabs ──────────────────────────────────────────────────────────────────
tab_query, tab_anomalies, tab_agents = st.tabs(
    ["💬 Ask a Question", "⚠️ Anomalies", "👤 Agent Performance"]
)


# ── Tab 1: NL Query ────────────────────────────────────────────────────────────
with tab_query:
    st.subheader("Ask anything about the tickets")

    example_queries = [
        "How many tickets are currently open?",
        "Which agent resolved the most tickets?",
        "Show me all Critical tickets not resolved within 12 hours",
        "What is the average customer rating for Technical category tickets?",
        "Which agent has the lowest average customer rating?",
        "How many high priority tickets are unresolved?",
        "What percentage of tickets are escalated?",
    ]

    chosen = st.selectbox("Try an example:", ["— pick one —"] + example_queries)
    question = st.text_input(
        "Your question:",
        value=chosen if chosen != "— pick one —" else "",
        placeholder="e.g. How many critical tickets are unresolved?",
    )

    if st.button("Ask", type="primary") and question.strip():
        with st.spinner("Thinking..."):
            result, err = api_post("/query", {"question": question})

        if err:
            st.error(err)
        else:
            st.success(result["answer"])

            if result["data"]:
                st.write(f"**{result['row_count']} row(s) returned**")
                df = pd.DataFrame(result["data"])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Query returned no rows.")


# ── Tab 2: Anomalies ──────────────────────────────────────────────────────────
with tab_anomalies:
    st.subheader("Detected Anomalies")
    st.caption("Rules: overdue high-priority tickets, IQR-based slow resolutions, 1-star ratings, suspiciously fast closes")

    data, err = api_get("/anomalies")

    if err:
        st.error(err)
    elif data:
        col_h, col_m, col_l = st.columns(3)
        col_h.metric("🔴 High", data["summary"]["high"])
        col_m.metric("🟡 Medium", data["summary"]["medium"])
        col_l.metric("🟢 Low", data["summary"]["low"])

        st.divider()

        if data["total"] == 0:
            st.success("No anomalies detected.")
        else:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            severity_order = {"high": 0, "medium": 1, "low": 2}

            sorted_anomalies = sorted(
                data["anomalies"],
                key=lambda x: severity_order.get(x["severity"], 3),
            )

            rows = []
            for a in sorted_anomalies:
                rows.append({
                    "Severity": severity_icon.get(a["severity"], "⚪") + " " + a["severity"].capitalize(),
                    "Ticket ID": a["ticket_id"],
                    "Type": a["anomaly_type"].replace("_", " ").title(),
                    "Description": a["description"],
                })

            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Tab 3: Agent Performance ──────────────────────────────────────────────────
with tab_agents:
    st.subheader("Agent Performance (Resolved Tickets Only)")

    stats, err = api_get("/stats")

    if err:
        st.error(err)
    else:
        df = pd.DataFrame(stats["agent_performance"])

        if df.empty:
            st.info("No resolved tickets found.")
        else:
            df.columns = ["Agent", "Tickets Resolved", "Avg Rating", "Avg Resolution (hrs)"]
            df = df.sort_values("Tickets Resolved", ascending=False)

            st.dataframe(df, use_container_width=True, hide_index=True)

            st.divider()
            col_a, col_b = st.columns(2)

            with col_a:
                st.write("**Tickets Resolved per Agent**")
                chart_df = df.set_index("Agent")["Tickets Resolved"]
                st.bar_chart(chart_df)

            with col_b:
                st.write("**Average Customer Rating per Agent**")
                rating_df = df.set_index("Agent")["Avg Rating"]
                st.bar_chart(rating_df)
