"""
AI Business Decision Copilot - Analytics Tools (Anomaly Detection + Root Cause Ranking)
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_anomaly_detection(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Detect anomalies in sales data using statistical methods.

    Args:
        df: Sales DataFrame.
        file_path: Path to sales CSV.

    Returns:
        dict with detected anomalies and their severity.
    """
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No data available for anomaly detection"}

    try:
        df["order_date"] = pd.to_datetime(df["order_date"])
        anomalies = []

        # Daily revenue anomaly (Z-score)
        daily_rev = df.groupby("order_date")["revenue"].sum().reset_index()
        daily_rev.columns = ["date", "revenue"]

        mean_rev = daily_rev["revenue"].mean()
        std_rev = daily_rev["revenue"].std()
        if std_rev > 0:
            daily_rev["z_score"] = ((daily_rev["revenue"] - mean_rev) / std_rev).round(2)
            anomaly_days = daily_rev[abs(daily_rev["z_score"]) > 2]
            for _, row in anomaly_days.iterrows():
                anomalies.append({
                    "type": "revenue_anomaly",
                    "date": str(row["date"].date()),
                    "value": round(float(row["revenue"]), 2),
                    "z_score": float(row["z_score"]),
                    "severity": "high" if abs(row["z_score"]) > 3 else "medium",
                    "direction": "below_normal" if row["z_score"] < 0 else "above_normal",
                })

        # Monthly revenue drop detection
        monthly = df.groupby(df["order_date"].dt.to_period("M"))["revenue"].sum().reset_index()
        monthly.columns = ["month", "revenue"]
        monthly["month"] = monthly["month"].astype(str)

        for i in range(1, len(monthly)):
            prev = monthly.iloc[i - 1]["revenue"]
            curr = monthly.iloc[i]["revenue"]
            change_pct = (curr - prev) / prev * 100 if prev > 0 else 0
            if change_pct < -10:
                anomalies.append({
                    "type": "monthly_revenue_drop",
                    "month": monthly.iloc[i]["month"],
                    "current_revenue": round(float(curr), 2),
                    "previous_revenue": round(float(prev), 2),
                    "change_pct": round(float(change_pct), 1),
                    "severity": "high" if change_pct < -20 else "medium",
                })

        # Category-level anomaly
        df["month"] = df["order_date"].dt.to_period("M").astype(str)
        months = sorted(df["month"].unique())
        if len(months) >= 2:
            last = months[-1]
            prev = months[-2]
            cat_last = df[df["month"] == last].groupby("category")["revenue"].sum()
            cat_prev = df[df["month"] == prev].groupby("category")["revenue"].sum()
            cat_change = ((cat_last - cat_prev) / cat_prev * 100).dropna()
            for cat, chg in cat_change.items():
                if chg < -15:
                    anomalies.append({
                        "type": "category_decline",
                        "category": cat,
                        "change_pct": round(float(chg), 1),
                        "severity": "high" if chg < -25 else "medium",
                    })

        return {
            "status": "success",
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "daily_stats": {
                "mean_daily_revenue": round(float(mean_rev), 2),
                "std_daily_revenue": round(float(std_rev), 2),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_root_cause_ranking(analysis_results: dict) -> list:
    """Rank root causes by combining signals from all agent analyses.

    Args:
        analysis_results: Combined output from all specialist agents.

    Returns:
        list of root causes ranked by confidence score.
    """
    root_causes = []

    # 1. Inventory stockouts
    inv = analysis_results.get("inventory_analysis", {})
    if inv.get("status") == "success" and inv.get("stockout_count", 0) > 0:
        stockout_count = inv["stockout_count"]
        confidence = min(0.95, 0.5 + stockout_count * 0.08)
        stockout_products = [p["product_id"] for p in inv.get("stockout_products", [])[:5]]
        root_causes.append({
            "cause": f"Stockout of {stockout_count} products including top sellers: {', '.join(stockout_products)}",
            "category": "Inventory",
            "confidence": round(confidence, 2),
            "impact": "high",
            "evidence": f"{stockout_count} products below reorder level, inventory risk score: {inv.get('inventory_risk_score', 0)}%",
            "recommendation": f"Immediately reorder {stockout_count} stockout products, prioritizing top sellers",
        })

    # 2. Marketing ROI decline
    mkt = analysis_results.get("marketing_analysis", {})
    if mkt.get("status") == "success" and mkt.get("roi_change", 0) < -10:
        roi_change = mkt["roi_change"]
        wasted = mkt.get("wasted_spend", 0)
        confidence = min(0.9, 0.4 + abs(roi_change) * 0.01)
        root_causes.append({
            "cause": f"Marketing ROI dropped {abs(roi_change):.0f}% with ${wasted:,.0f} in wasted spend",
            "category": "Marketing",
            "confidence": round(confidence, 2),
            "impact": "high" if abs(roi_change) > 20 else "medium",
            "evidence": f"ROI change: {roi_change:.1f}%, wasted spend on underperforming campaigns: ${wasted:,.2f}",
            "recommendation": "Pause underperforming campaigns and reallocate budget to high-ROI channels",
        })

    # 3. Customer complaint spike
    sup = analysis_results.get("support_analysis", {})
    if sup.get("status") == "success" and sup.get("has_complaint_spike", False):
        ticket_change = sup.get("ticket_change_pct", 0)
        neg_pct = sup.get("negative_sentiment_pct", 0)
        top_issue = sup.get("issue_distribution", [{}])[0].get("issue_type", "Unknown") if sup.get("issue_distribution") else "Unknown"
        confidence = min(0.85, 0.35 + ticket_change * 0.005)
        root_causes.append({
            "cause": f"Customer complaints increased {ticket_change:.0f}%, mainly '{top_issue}' ({neg_pct:.0f}% negative sentiment)",
            "category": "Customer Support",
            "confidence": round(confidence, 2),
            "impact": "high" if ticket_change > 30 else "medium",
            "evidence": f"Ticket increase: {ticket_change:.1f}%, top issue: {top_issue}, negative sentiment: {neg_pct:.1f}%",
            "recommendation": f"Investigate '{top_issue}' complaints and implement corrective action",
        })

    # 4. Sales decline by product/category
    sales = analysis_results.get("sales_analysis", {})
    if sales.get("status") == "success" and sales.get("revenue_change_pct", 0) < -10:
        rev_change = sales["revenue_change_pct"]
        declining = sales.get("declining_products", [])
        confidence = min(0.8, 0.3 + abs(rev_change) * 0.01)
        root_causes.append({
            "cause": f"Revenue declined {abs(rev_change):.1f}% with {len(declining)} products showing >10% drop",
            "category": "Sales",
            "confidence": round(confidence, 2),
            "impact": "high",
            "evidence": f"Revenue change: {rev_change:.1f}%, {len(declining)} declining products",
            "recommendation": "Review pricing strategy and promotional calendar for declining products",
        })

    # Sort by confidence
    root_causes.sort(key=lambda x: x["confidence"], reverse=True)

    return root_causes
