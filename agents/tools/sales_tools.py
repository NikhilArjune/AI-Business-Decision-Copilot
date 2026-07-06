"""
AI Business Decision Copilot - Sales Analysis Tools

Provides revenue and sales performance analysis — the foundation of most
business diagnostic questions. When a business owner asks "why did revenue
decrease?", the Sales Agent uses this tool to quantify the decline and
identify which products, categories, and regions are driving it.

Business Context:
    Sales data is typically the most granular dataset, with one row per
    order line item. Expected columns: order_id, order_date, product_id,
    category, region, quantity, revenue.

Key Metrics Computed:
    - Monthly revenue trends (time series for charting)
    - Month-over-month revenue change (% and absolute)
    - Product-level performance ranking (top 10, bottom 10)
    - Category-level aggregation (which product categories are growing/declining)
    - Regional performance (geographic breakdown)
    - Declining products (>10% month-over-month drop — early warning signal)
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_sales_analysis(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Analyze sales data for revenue trends, product performance, and regional patterns.

    This tool accepts data either as a DataFrame (when called programmatically
    from the pipeline) or as a file path (when called via MCP by the ADK agent).
    This dual-input design allows the same tool to work in both execution modes.

    Analysis Steps:
        1. Parse dates and create month/week columns for time-series grouping
        2. Aggregate monthly revenue, orders, quantity, and average order value
        3. Calculate month-over-month revenue change (the key metric)
        4. Rank products by total revenue (top 10 and bottom 10)
        5. Group by category and region for dimensional analysis
        6. Detect declining products (>10% MoM drop) as early warning signals

    Args:
        df: Sales DataFrame (used when called from the backend pipeline).
        file_path: Path to sales CSV (used when called via MCP server).

    Returns:
        dict containing:
            - monthly_revenue: time series data for charting
            - revenue_change_pct: month-over-month change percentage
            - top_products / bottom_products: ranked product lists
            - declining_products: products with >10% revenue drop
            - category_performance / region_performance: dimensional breakdowns
    """
    # Handle dual input: DataFrame (programmatic) or file path (MCP)
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No sales data available"}

    try:
        # ── Time-series preparation ──────────────────────────────────
        df["order_date"] = pd.to_datetime(df["order_date"])
        df["month"] = df["order_date"].dt.to_period("M").astype(str)
        df["week"] = df["order_date"].dt.isocalendar().week.astype(int)

        # ── Monthly revenue aggregation ──────────────────────────────
        # This is the primary time-series data used for trend visualization
        monthly = df.groupby("month").agg(
            total_revenue=("revenue", "sum"),
            total_orders=("order_id", "nunique"),
            total_quantity=("quantity", "sum"),
            avg_order_value=("revenue", "mean"),
        ).reset_index()
        monthly = monthly.sort_values("month")

        # ── Month-over-month revenue change ──────────────────────────
        # This is the key metric — answers "did revenue go up or down?"
        # Compare the most recent month to the one before it.
        if len(monthly) >= 2:
            current = monthly.iloc[-1]["total_revenue"]
            previous = monthly.iloc[-2]["total_revenue"]
            revenue_change = current - previous
            revenue_change_pct = ((current - previous) / previous * 100) if previous > 0 else 0
        else:
            revenue_change = 0
            revenue_change_pct = 0

        # ── Product-level performance ranking ────────────────────────
        # Identifies the best and worst performing products by total revenue
        product_perf = df.groupby("product_id").agg(
            revenue=("revenue", "sum"),
            quantity=("quantity", "sum"),
            orders=("order_id", "nunique"),
        ).reset_index().sort_values("revenue", ascending=False)

        top_products = product_perf.head(10).to_dict(orient="records")
        bottom_products = product_perf.tail(10).to_dict(orient="records")

        # ── Category-level aggregation ───────────────────────────────
        # Groups products into categories (e.g., Electronics, Apparel)
        # to identify which business segments are growing or declining
        category_perf = df.groupby("category").agg(
            revenue=("revenue", "sum"),
            quantity=("quantity", "sum"),
            orders=("order_id", "nunique"),
        ).reset_index().sort_values("revenue", ascending=False)

        # ── Regional performance ─────────────────────────────────────
        # Geographic breakdown helps identify region-specific issues
        # (e.g., delivery problems in one region affecting sales there)
        region_perf = df.groupby("region").agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
        ).reset_index().sort_values("revenue", ascending=False)

        # ── Declining product detection ──────────────────────────────
        # Compare each product's revenue between the last two months.
        # Products with >10% decline are flagged as early warning signals.
        # This threshold catches meaningful declines while avoiding
        # false positives from normal sales variation.
        if len(monthly) >= 2:
            last_month = monthly.iloc[-1]["month"]
            prev_month = monthly.iloc[-2]["month"]
            last_month_products = df[df["month"] == last_month].groupby("product_id")["revenue"].sum()
            prev_month_products = df[df["month"] == prev_month].groupby("product_id")["revenue"].sum()
            product_changes = ((last_month_products - prev_month_products) / prev_month_products * 100).dropna()
            declining = product_changes[product_changes < -10].sort_values()
            declining_products = [
                {"product_id": pid, "change_pct": round(float(chg), 1)}
                for pid, chg in declining.head(10).items()
            ]
        else:
            declining_products = []

        return {
            "status": "success",
            "monthly_revenue": monthly.to_dict(orient="records"),
            "revenue_change": round(float(revenue_change), 2),
            "revenue_change_pct": round(float(revenue_change_pct), 1),
            "total_revenue": round(float(df["revenue"].sum()), 2),
            "total_orders": int(df["order_id"].nunique()),
            "avg_order_value": round(float(df["revenue"].mean()), 2),
            "top_products": top_products,
            "bottom_products": bottom_products,
            "declining_products": declining_products,
            "category_performance": category_perf.to_dict(orient="records"),
            "region_performance": region_perf.to_dict(orient="records"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
