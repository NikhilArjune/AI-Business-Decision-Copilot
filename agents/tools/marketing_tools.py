"""
AI Business Decision Copilot - Marketing Analysis Tools
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_marketing_analysis(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Analyze marketing campaign data: ROI, conversion rates, channel performance.

    Args:
        df: Marketing DataFrame.
        file_path: Path to marketing CSV.

    Returns:
        dict with campaign ROI, channel performance, underperforming campaigns.
    """
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No marketing data available"}

    try:
        # Calculate metrics
        df["roi"] = ((df["revenue_generated"] - df["spend"]) / df["spend"] * 100).round(1)
        df["cpa"] = (df["spend"] / df["conversions"].replace(0, np.nan)).round(2)
        df["ctr"] = (df["clicks"] / df["impressions"].replace(0, np.nan) * 100).round(2)
        df["conversion_rate"] = (df["conversions"] / df["clicks"].replace(0, np.nan) * 100).round(2)

        # Channel performance
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

        # Monthly trend
        if "month" in df.columns:
            monthly = df.groupby("month").agg(
                total_spend=("spend", "sum"),
                total_revenue=("revenue_generated", "sum"),
                total_conversions=("conversions", "sum"),
            ).reset_index()
            monthly["roi"] = ((monthly["total_revenue"] - monthly["total_spend"]) / monthly["total_spend"] * 100).round(1)
            monthly = monthly.sort_values("month")

            # ROI change
            if len(monthly) >= 2:
                current_roi = monthly.iloc[-1]["roi"]
                prev_roi = monthly.iloc[-2]["roi"]
                roi_change = float(current_roi - prev_roi)
            else:
                roi_change = 0.0
        else:
            monthly = pd.DataFrame()
            roi_change = 0.0

        # Underperforming campaigns (negative ROI)
        underperforming = df[df["roi"] < 0].sort_values("roi")[
            ["campaign_id", "channel", "spend", "revenue_generated", "roi", "conversions"]
        ].to_dict(orient="records")

        # Best performing campaigns
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
            "wasted_spend": round(float(df[df["roi"] < 0]["spend"].sum()), 2),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
