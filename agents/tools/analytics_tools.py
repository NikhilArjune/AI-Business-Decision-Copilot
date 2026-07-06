"""
AI Business Decision Copilot - Analytics Tools (Anomaly Detection + Root Cause Ranking)

This is the synthesis layer of the pipeline. It contains two complementary
tools:

    run_anomaly_detection — the statistical eye. It scans sales data for
        outliers (unusual days, sharp monthly drops, collapsing categories)
        using Z-scores and threshold comparisons. It answers "*where* is
        something abnormal?" without needing context from other domains.

    run_root_cause_ranking — the reasoning eye. It fuses the findings from
        every domain agent (sales, inventory, marketing, support) into a
        single confidence-scored, ranked list of probable causes. It answers
        "*why* did revenue move, and how sure are we?"

Together they turn four independent domain reports into one prioritized
explanation that the Recommendation and Report agents build on.
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_anomaly_detection(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Detect statistical anomalies in sales data at three granularities.

    Accepts data as a DataFrame (backend pipeline) or a file path (ADK/MCP
    agent), so the same logic serves both execution modes.

    Business Logic — three detectors run in sequence:
        1. Daily revenue outliers via Z-score: any day more than 2 standard
           deviations from the mean daily revenue is flagged. |Z|>3 is "high"
           severity, |Z|>2 is "medium". Direction (above/below normal) is
           recorded because a spike and a crash mean very different things.
        2. Monthly revenue drops: any month down >10% vs the prior month is
           flagged (>20% = high). This catches sustained decline that daily
           noise might mask.
        3. Category declines: any category down >15% month-over-month is
           flagged (>25% = high) — pinpoints which product line is bleeding.

    The Z-score approach is preferred over a fixed dollar threshold because it
    self-scales to each business's revenue level — a $10k dip is an anomaly
    for a small shop but noise for a large one.

    Args:
        df: Sales DataFrame (used from the backend pipeline).
        file_path: Path to sales CSV (used via the MCP server).

    Returns:
        dict with an anomaly count, the list of anomalies (typed and
        severity-tagged), and daily revenue mean/std for context.
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

        # ── Detector 1: Daily revenue outliers (Z-score) ─────────────
        # Total revenue per day, then measure how many standard deviations
        # each day sits from the mean. std must be > 0 to divide safely
        # (a flat revenue series has no deviation and thus no outliers).
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

        # ── Detector 2: Monthly revenue drops ────────────────────────
        # Walk consecutive months and flag any >10% decline. This surfaces
        # sustained downturns that day-level noise can obscure.
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

        # ── Detector 3: Category-level declines ──────────────────────
        # Compare the two most recent months per category and flag any
        # category down >15%. Narrows a top-line drop to the specific
        # product line responsible.
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
    """Fuse all domain findings into a ranked, confidence-scored cause list.

    This is the heart of the "why did this happen?" answer. It inspects each
    domain's results and, where a domain crosses its warning threshold, emits
    a candidate root cause with a confidence score, an impact rating, the
    supporting evidence, and a concrete recommendation.

    Confidence model:
        Each cause starts from a domain-specific base confidence and grows
        with the severity of the signal, capped so no single heuristic ever
        claims certainty. For example, stockouts start at 0.50 and add 0.08
        per affected product (capped at 0.95): more stockouts → higher
        confidence that inventory is the culprit. The caps (0.95/0.90/0.85/
        0.80) also encode a rough prior over how *directly* each domain drives
        revenue — inventory stockouts are the most direct, so they cap highest.

    Only domains that (a) ran successfully and (b) breached their threshold
    contribute a cause, which keeps the output focused on real problems rather
    than listing every metric. The final list is sorted by confidence so the
    most likely explanation leads.

    Args:
        analysis_results: Combined output keyed by "<domain>_analysis"
            (sales_analysis, inventory_analysis, marketing_analysis,
            support_analysis), as assembled by the pipeline.

    Returns:
        list of root cause dicts (cause, category, confidence, impact,
        evidence, recommendation), sorted by confidence descending.
    """
    root_causes = []

    # ── Signal 1: Inventory stockouts (most direct revenue impact) ───
    # Confidence scales with how many products are out of stock. Capped at
    # 0.95 because a stockout is close to a guaranteed cause of lost sales.
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

    # ── Signal 2: Marketing ROI decline ──────────────────────────────
    # Triggers only on a meaningful drop (>10% ROI decline). Confidence grows
    # with the size of the drop, capped at 0.90 — marketing affects revenue
    # strongly but less immediately than an outright stockout.
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

    # ── Signal 3: Customer complaint spike ───────────────────────────
    # Triggers on the support agent's spike flag. Confidence grows with the
    # size of the ticket increase, capped at 0.85 — complaints are a lagging
    # indicator, so they corroborate a cause more than they prove one.
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

    # ── Signal 4: Sales decline by product/category ──────────────────
    # Triggers on a >10% month-over-month revenue drop. Capped at 0.80: the
    # sales drop is the *symptom* being explained, so on its own it is the
    # weakest "cause" — the other three signals explain what drove it.
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

    # Rank so the most probable explanation is first — downstream stages
    # (recommendations, report, overall confidence score) all read the top cause.
    root_causes.sort(key=lambda x: x["confidence"], reverse=True)

    return root_causes
