"""
AI Business Decision Copilot - Inventory Analysis Tools

Detects supply-chain problems that translate directly into lost revenue.
Stockouts are one of the most common — and most preventable — causes of a
revenue drop: a product that can't be sold generates zero revenue no matter
how strong demand is. The Inventory Agent uses this tool to surface those
gaps so they can be cross-referenced against declining sales.

Business Context:
    Inventory data is a snapshot of current stock levels, typically one row
    per SKU. Expected columns: product_id, category, stock_available,
    reorder_level. Optional columns: blocked_stock, unit_cost.

Key Signals Computed:
    - Stockouts: products at or below zero sellable stock (immediate revenue loss)
    - Low stock: products above zero but below their reorder threshold (imminent risk)
    - Blocked inventory: physical stock that exists but cannot be sold
      (damaged, quarantined, reserved) — capital tied up with no return
    - Inventory risk score: a single 0-100 gauge of overall supply health
"""

import pandas as pd
import numpy as np
from typing import Optional


def run_inventory_analysis(df: Optional[pd.DataFrame] = None, file_path: str = "") -> dict:
    """Analyze inventory data for stockouts, low stock, and blocked inventory.

    Like the other domain tools, this accepts data either as a DataFrame
    (backend pipeline path) or a file path (ADK/MCP agent path), so the same
    logic serves both execution modes.

    Business Logic:
        - A product is a "stockout" when sellable stock is <= 0. These are the
          highest-priority items because they are actively losing sales.
        - A product is "low stock" when it still has stock but has fallen below
          its reorder_level — a leading indicator of a future stockout.
        - "Blocked" stock is on hand but unsellable; when unit_cost is present
          we value it to quantify the trapped capital.
        - The risk score weights stockouts fully and low-stock at half
          (they are a warning, not yet a loss), normalized by catalog size,
          then bucketed into Low/Medium/High/Critical for at-a-glance triage.

    Args:
        df: Inventory DataFrame (used when called from the backend pipeline).
        file_path: Path to inventory CSV (used when called via MCP server).

    Returns:
        dict with stockout/low-stock/blocked product lists, per-category
        summary, an inventory risk score (0-100), and a risk level label.
    """
    if df is None and file_path:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if df is None or df.empty:
        return {"status": "error", "message": "No inventory data available"}

    try:
        # ── Classify each SKU by stock health ────────────────────────
        # Stockout: no sellable stock at all → actively losing sales.
        # Low stock: has stock but below its reorder trigger → imminent risk.
        # Blocked: stock exists but is flagged unsellable (default 0 if the
        # column is absent, so the analysis still runs on minimal schemas).
        df["is_stockout"] = df["stock_available"] <= 0
        df["is_low_stock"] = (df["stock_available"] > 0) & (df["stock_available"] < df["reorder_level"])
        df["is_blocked"] = df.get("blocked_stock", pd.Series([0] * len(df))) > 0

        stockout_products = df[df["is_stockout"]][["product_id", "category", "stock_available", "reorder_level"]].to_dict(orient="records")
        low_stock_products = df[df["is_low_stock"]][["product_id", "category", "stock_available", "reorder_level"]].to_dict(orient="records")

        # ── Blocked inventory valuation ──────────────────────────────
        # Blocked stock is capital sitting idle. When unit_cost is available
        # we total its value so the report can quantify the trapped money.
        if "blocked_stock" in df.columns:
            blocked_products = df[df["blocked_stock"] > 0][["product_id", "category", "blocked_stock"]].to_dict(orient="records")
            total_blocked_value = 0
            if "unit_cost" in df.columns:
                total_blocked_value = float((df["blocked_stock"] * df["unit_cost"]).sum())
        else:
            blocked_products = []
            total_blocked_value = 0

        # ── Category-level summary ───────────────────────────────────
        # Rolls the per-SKU flags up to category so the report can point at
        # which product lines (e.g. Electronics) carry the most supply risk.
        category_summary = df.groupby("category").agg(
            total_products=("product_id", "count"),
            stockouts=("is_stockout", "sum"),
            low_stock=("is_low_stock", "sum"),
            avg_stock=("stock_available", "mean"),
        ).reset_index().to_dict(orient="records")

        # ── Risk scoring ─────────────────────────────────────────────
        # Single 0-100 gauge of supply health. Stockouts count fully (already
        # costing sales); low-stock counts at half weight (a warning, not yet
        # a loss). Dividing by catalog size makes the score comparable across
        # datasets of different sizes. Thresholds below bucket it for triage.
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
