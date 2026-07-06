"""
AI Business Decision Copilot - Support Ticket Analysis Tools
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_support_analysis(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Analyze customer support tickets: complaints, sentiment, spikes.

    Args:
        df: Support tickets DataFrame.
        file_path: Path to support tickets CSV.

    Returns:
        dict with complaint categories, sentiment breakdown, ticket spikes.
    """
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No support data available"}

    try:
        df["created_date"] = pd.to_datetime(df["created_date"])
        df["month"] = df["created_date"].dt.to_period("M").astype(str)

        # Issue type distribution
        issue_counts = df["issue_type"].value_counts().to_dict()
        issue_dist = [{"issue_type": k, "count": int(v), "pct": round(v / len(df) * 100, 1)} for k, v in issue_counts.items()]

        # Sentiment breakdown
        sentiment_counts = df["sentiment"].value_counts().to_dict()
        sentiment_dist = {k: int(v) for k, v in sentiment_counts.items()}
        negative_pct = round(sentiment_counts.get("negative", 0) / max(len(df), 1) * 100, 1)

        # Monthly trend
        monthly = df.groupby("month").agg(
            total_tickets=("ticket_id", "count"),
            negative_tickets=("sentiment", lambda x: (x == "negative").sum()),
        ).reset_index()
        monthly["negative_pct"] = (monthly["negative_tickets"] / monthly["total_tickets"] * 100).round(1)
        monthly = monthly.sort_values("month")

        # Ticket spike detection
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

        # Top complained products
        product_complaints = df.groupby("product_id").agg(
            complaints=("ticket_id", "count"),
            negative=("sentiment", lambda x: (x == "negative").sum()),
        ).reset_index().sort_values("complaints", ascending=False)
        top_complained = product_complaints.head(10).to_dict(orient="records")

        # Resolution time stats
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
