"""
AI Business Decision Copilot - Sales Analysis Tools
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_sales_analysis(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Analyze sales data: revenue trends, product performance, regional breakdown.

    Args:
        df: Sales DataFrame (optional, used when called programmatically).
        file_path: Path to sales CSV (used when called via MCP).

    Returns:
        dict with revenue trends, top/bottom products, regional performance.
    """
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No sales data available"}

    try:
        df["order_date"] = pd.to_datetime(df["order_date"])
        df["month"] = df["order_date"].dt.to_period("M").astype(str)
        df["week"] = df["order_date"].dt.isocalendar().week.astype(int)

        # Monthly revenue
        monthly = df.groupby("month").agg(
            total_revenue=("revenue", "sum"),
            total_orders=("order_id", "nunique"),
            total_quantity=("quantity", "sum"),
            avg_order_value=("revenue", "mean"),
        ).reset_index()
        monthly = monthly.sort_values("month")

        # Month-over-month change
        if len(monthly) >= 2:
            current = monthly.iloc[-1]["total_revenue"]
            previous = monthly.iloc[-2]["total_revenue"]
            revenue_change = current - previous
            revenue_change_pct = ((current - previous) / previous * 100) if previous > 0 else 0
        else:
            revenue_change = 0
            revenue_change_pct = 0

        # Product performance
        product_perf = df.groupby("product_id").agg(
            revenue=("revenue", "sum"),
            quantity=("quantity", "sum"),
            orders=("order_id", "nunique"),
        ).reset_index().sort_values("revenue", ascending=False)

        top_products = product_perf.head(10).to_dict(orient="records")
        bottom_products = product_perf.tail(10).to_dict(orient="records")

        # Category performance
        category_perf = df.groupby("category").agg(
            revenue=("revenue", "sum"),
            quantity=("quantity", "sum"),
            orders=("order_id", "nunique"),
        ).reset_index().sort_values("revenue", ascending=False)

        # Regional performance
        region_perf = df.groupby("region").agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
        ).reset_index().sort_values("revenue", ascending=False)

        # Declining products (compare last 2 months)
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
