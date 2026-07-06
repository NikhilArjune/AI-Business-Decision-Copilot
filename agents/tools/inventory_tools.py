"""
AI Business Decision Copilot - Inventory Analysis Tools
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_inventory_analysis(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Analyze inventory data: stockouts, slow-moving products, blocked inventory.

    Args:
        df: Inventory DataFrame.
        file_path: Path to inventory CSV.

    Returns:
        dict with stockout alerts, slow-moving SKUs, inventory risk summary.
    """
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No inventory data available"}

    try:
        # Stockout detection: stock below reorder level
        df["is_stockout"] = df["stock_available"] <= 0
        df["is_low_stock"] = (df["stock_available"] > 0) & (df["stock_available"] < df["reorder_level"])
        df["is_blocked"] = df.get("blocked_stock", pd.Series([0] * len(df))) > 0

        stockout_products = df[df["is_stockout"]][["product_id", "category", "stock_available", "reorder_level"]].to_dict(orient="records")
        low_stock_products = df[df["is_low_stock"]][["product_id", "category", "stock_available", "reorder_level"]].to_dict(orient="records")

        # Blocked inventory
        if "blocked_stock" in df.columns:
            blocked_products = df[df["blocked_stock"] > 0][["product_id", "category", "blocked_stock"]].to_dict(orient="records")
            total_blocked_value = 0
            if "unit_cost" in df.columns:
                total_blocked_value = float((df["blocked_stock"] * df["unit_cost"]).sum())
        else:
            blocked_products = []
            total_blocked_value = 0

        # Category-level summary
        category_summary = df.groupby("category").agg(
            total_products=("product_id", "count"),
            stockouts=("is_stockout", "sum"),
            low_stock=("is_low_stock", "sum"),
            avg_stock=("stock_available", "mean"),
        ).reset_index().to_dict(orient="records")

        # Risk scoring
        total_products = len(df)
        stockout_count = int(df["is_stockout"].sum())
        low_stock_count = int(df["is_low_stock"].sum())
        risk_score = round((stockout_count + low_stock_count * 0.5) / max(total_products, 1) * 100, 1)

        return {
            "status": "success",
            "total_products": total_products,
            "stockout_count": stockout_count,
            "low_stock_count": low_stock_count,
            "stockout_products": stockout_products,
            "low_stock_products": low_stock_products,
            "blocked_products": blocked_products,
            "total_blocked_value": round(total_blocked_value, 2),
            "category_summary": category_summary,
            "inventory_risk_score": risk_score,
            "risk_level": "Critical" if risk_score > 30 else "High" if risk_score > 15 else "Medium" if risk_score > 5 else "Low",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
