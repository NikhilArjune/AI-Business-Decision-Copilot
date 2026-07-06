"""
AI Business Decision Copilot - Support Ticket Analysis Tools

Turns the customer support inbox into a business signal. Complaints are a
lagging indicator: a spike in "delivery delay" tickets, for example, often
trails a fulfillment problem that is simultaneously suppressing repeat
purchases. The Support Agent uses this tool to detect those spikes and the
sentiment behind them so they can be correlated with revenue changes.

Business Context:
    Support data is one row per ticket. Expected columns: ticket_id,
    created_date, issue_type, sentiment, product_id. Optional:
    resolution_time_hours.

Key Signals Computed:
    - Issue distribution: which complaint categories dominate
    - Sentiment breakdown: share of positive/neutral/negative tickets
    - Ticket volume trend and spike detection (>20% MoM = emerging problem)
    - Top-complained products: where dissatisfaction concentrates
    - Resolution time: how fast issues are being closed
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_support_analysis(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Analyze support tickets for complaint categories, sentiment, and spikes.

    Accepts data as a DataFrame (backend pipeline) or a file path (ADK/MCP
    agent), so the same logic serves both execution modes.

    Business Logic:
        - Issue and sentiment distributions quantify *what* customers complain
          about and *how* they feel — negative_pct is the headline sentiment KPI.
        - Spike detection compares the latest month's ticket volume to the
          prior month; a >20% jump is flagged as an emerging issue worth
          investigating (the threshold filters out normal week-to-week noise).
        - Product-level complaint counts localize the problem to specific SKUs,
          which lets the analytics layer tie complaints back to sales declines.
        - Resolution time (when present) reveals whether the support team is
          keeping pace or falling behind on the incoming volume.

    Args:
        df: Support tickets DataFrame (used from the backend pipeline).
        file_path: Path to support tickets CSV (used via the MCP server).

    Returns:
        dict with issue/sentiment distributions, monthly trend, spike flag,
        top-complained products, and resolution-time stats.
    """
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No support data available"}

    try:
        # Parse dates and bucket tickets by month for trend/spike analysis.
        df["created_date"] = pd.to_datetime(df["created_date"])
        df["month"] = df["created_date"].dt.to_period("M").astype(str)

        # ── Issue type distribution ──────────────────────────────────
        # Ranks complaint categories with their share of total volume so the
        # report can name the dominant pain point (e.g. "40% delivery delays").
        issue_counts = df["issue_type"].value_counts().to_dict()
        issue_dist = [{"issue_type": k, "count": int(v), "pct": round(v / len(df) * 100, 1)} for k, v in issue_counts.items()]

        # ── Sentiment breakdown ──────────────────────────────────────
        # negative_pct is the single sentiment KPI carried downstream — a high
        # value signals customers are unhappy, not just numerous.
        sentiment_counts = df["sentiment"].value_counts().to_dict()
        sentiment_dist = {k: int(v) for k, v in sentiment_counts.items()}
        negative_pct = round(sentiment_counts.get("negative", 0) / max(len(df), 1) * 100, 1)

        # ── Monthly volume trend ─────────────────────────────────────
        # Tracks total and negative tickets per month; the last two months
        # feed the spike test below.
        monthly = df.groupby("month").agg(
            total_tickets=("ticket_id", "count"),
            negative_tickets=("sentiment", lambda x: (x == "negative").sum()),
        ).reset_index()
        monthly["negative_pct"] = (monthly["negative_tickets"] / monthly["total_tickets"] * 100).round(1)
        monthly = monthly.sort_values("month")

        # ── Ticket spike detection ───────────────────────────────────
        # A >20% month-over-month jump in ticket volume is treated as an
        # emerging issue. The 20% threshold is high enough to ignore ordinary
        # fluctuation but low enough to catch a real problem early.
        if len(monthly) >= 2:
            current_tickets = int(monthly.iloc[-1]["total_tickets"])
            prev_tickets = int(monthly.iloc[-2]["total_tickets"])
            ticket_change = current_tickets - prev_tickets
            ticket_change_pct = round((ticket_change / max(prev_tickets, 1)) * 100, 1)
            has_spike = ticket_change_pct > 20
        else:
            current_tickets = int(monthly.iloc[-1]["total_tickets"]) if len(monthly) > 0 else 0
            ticket_change_pct = 0
            has_spike = False

        # ── Top complained products ──────────────────────────────────
        # Concentrating complaints by product_id lets the analytics layer link
        # dissatisfaction to the same SKUs that show declining sales.
        product_complaints = df.groupby("product_id").agg(
            complaints=("ticket_id", "count"),
            negative=("sentiment", lambda x: (x == "negative").sum()),
        ).reset_index().sort_values("complaints", ascending=False)
        top_complained = product_complaints.head(10).to_dict(orient="records")

        # ── Resolution time stats ────────────────────────────────────
        # Optional: indicates whether the support team is keeping up. A rising
        # average alongside a spike suggests the team is overwhelmed.
        if "resolution_time_hours" in df.columns:
            avg_resolution = round(float(df["resolution_time_hours"].mean()), 1)
            max_resolution = round(float(df["resolution_time_hours"].max()), 1)
        else:
            avg_resolution = None
            max_resolution = None

        return {
            "status": "success",
            "total_tickets": len(df),
            "issue_distribution": issue_dist,
            "sentiment_distribution": sentiment_dist,
            "negative_sentiment_pct": negative_pct,
            "monthly_trend": monthly.to_dict(orient="records"),
            "ticket_change_pct": ticket_change_pct,
            "has_complaint_spike": has_spike,
            "top_complained_products": top_complained,
            "avg_resolution_hours": avg_resolution,
            "max_resolution_hours": max_resolution,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
