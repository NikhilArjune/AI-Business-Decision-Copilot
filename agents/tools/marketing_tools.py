"""
AI Business Decision Copilot - Marketing Analysis Tools

Evaluates whether marketing spend is actually producing returns. Poor
marketing ROI is a frequently overlooked cause of revenue decline: the money
leaves the account but never converts into sales, so top-line growth stalls
even though "spend" looks healthy. The Marketing Agent uses this tool to find
the leaks — negative-ROI campaigns and underperforming channels.

Business Context:
    Marketing data is typically one row per campaign (optionally per month).
    Expected columns: campaign_id, channel, spend, revenue_generated,
    conversions, clicks, impressions. Optional: month (for trend analysis).

Key Metrics Computed:
    - ROI per campaign: (revenue - spend) / spend × 100
    - CPA (cost per acquisition): spend / conversions
    - CTR (click-through rate) and conversion rate: funnel efficiency
    - Channel comparison: which channels return the most per dollar
    - ROI trend: is marketing getting more or less efficient over time?
    - Wasted spend: total dollars poured into negative-ROI campaigns
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_marketing_analysis(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Analyze marketing campaigns for ROI, channel performance, and waste.

    Accepts data as a DataFrame (backend pipeline) or a file path (ADK/MCP
    agent), so the same logic serves both execution modes.

    Business Logic:
        - Per-campaign metrics are computed first (ROI, CPA, CTR, conversion
          rate). Division guards (replace(0, NaN)) prevent divide-by-zero for
          campaigns with no conversions/clicks/impressions.
        - Channel-level ROI uses aggregate spend and revenue rather than an
          average of per-campaign ROIs — this correctly weights big-budget
          campaigns instead of letting a tiny high-ROI campaign skew a channel.
        - The monthly trend and roi_change capture direction: a falling ROI is
          the signal that feeds root-cause ranking downstream.
        - Wasted spend sums the budget on every negative-ROI campaign — the
          concrete dollar figure a business owner can act on immediately.

    Args:
        df: Marketing DataFrame (used when called from the backend pipeline).
        file_path: Path to marketing CSV (used when called via MCP server).

    Returns:
        dict with overall/per-channel ROI, monthly trend, ROI change,
        best and underperforming campaigns, and total wasted spend.
    """
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No marketing data available"}

    try:
        # ── Per-campaign efficiency metrics ──────────────────────────
        # ROI is the headline number: profit per dollar spent, as a percent.
        # CPA/CTR/conversion_rate describe the funnel. replace(0, NaN) avoids
        # divide-by-zero for campaigns with no conversions/clicks/impressions.
        df["roi"] = ((df["revenue_generated"] - df["spend"]) / df["spend"] * 100).round(1)
        df["cpa"] = (df["spend"] / df["conversions"].replace(0, np.nan)).round(2)
        df["ctr"] = (df["clicks"] / df["impressions"].replace(0, np.nan) * 100).round(2)
        df["conversion_rate"] = (df["conversions"] / df["clicks"].replace(0, np.nan) * 100).round(2)

        # ── Channel performance ──────────────────────────────────────
        # Compare channels (e.g. Email, Paid Search) by return per dollar.
        # overall_roi is derived from summed spend/revenue, not an average of
        # per-campaign ROIs, so large campaigns are weighted correctly.
        channel_perf = df.groupby("channel").agg(
            total_spend=("spend", "sum"),
            total_revenue=("revenue_generated", "sum"),
            total_conversions=("conversions", "sum"),
            total_clicks=("clicks", "sum"),
            total_impressions=("impressions", "sum"),
            avg_roi=("roi", "mean"),
        ).reset_index()
        channel_perf["overall_roi"] = ((channel_perf["total_revenue"] - channel_perf["total_spend"]) / channel_perf["total_spend"] * 100).round(1)
        channel_perf = channel_perf.sort_values("overall_roi", ascending=False)

        # ── Monthly ROI trend ────────────────────────────────────────
        # If the data carries a month column, track ROI over time so we can
        # tell whether marketing efficiency is improving or deteriorating.
        if "month" in df.columns:
            monthly = df.groupby("month").agg(
                total_spend=("spend", "sum"),
                total_revenue=("revenue_generated", "sum"),
                total_conversions=("conversions", "sum"),
            ).reset_index()
            monthly["roi"] = ((monthly["total_revenue"] - monthly["total_spend"]) / monthly["total_spend"] * 100).round(1)
            monthly = monthly.sort_values("month")

            # Month-over-month ROI delta (percentage points). A negative value
            # here is the primary decline signal consumed by root-cause ranking.
            if len(monthly) >= 2:
                current_roi = monthly.iloc[-1]["roi"]
                prev_roi = monthly.iloc[-2]["roi"]
                roi_change = float(current_roi - prev_roi)
            else:
                roi_change = 0.0
        else:
            monthly = pd.DataFrame()
            roi_change = 0.0

        # ── Campaign winners and losers ──────────────────────────────
        # Underperforming = negative ROI (spending more than it returns).
        # These are the immediate candidates to pause or rework.
        underperforming = df[df["roi"] < 0].sort_values("roi")[
            ["campaign_id", "channel", "spend", "revenue_generated", "roi", "conversions"]
        ].to_dict(orient="records")

        # Best campaigns are the top 5 by ROI — the channels/creatives to
        # reinvest the reclaimed budget into.
        best = df.nlargest(5, "roi")[
            ["campaign_id", "channel", "spend", "revenue_generated", "roi", "conversions"]
        ].to_dict(orient="records")

        total_spend = float(df["spend"].sum())
        total_revenue = float(df["revenue_generated"].sum())

        return {
            "status": "success",
            "total_spend": round(total_spend, 2),
            "total_revenue_generated": round(total_revenue, 2),
            "overall_roi": round((total_revenue - total_spend) / max(total_spend, 1) * 100, 1),
            "roi_change": round(roi_change, 1),
            "total_conversions": int(df["conversions"].sum()),
            "channel_performance": channel_perf.to_dict(orient="records"),
            "monthly_trend": monthly.to_dict(orient="records") if not monthly.empty else [],
            "underperforming_campaigns": underperforming,
            "best_campaigns": best,
            # Total budget lost to negative-ROI campaigns — the reclaimable dollars.
            "wasted_spend": round(float(df[df["roi"] < 0]["spend"].sum()), 2),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
