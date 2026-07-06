"""
AI Business Decision Copilot - Report Generation Tools
"""

import json
from datetime import datetime, timezone
from typing import Optional


def generate_report(query: str, analysis: dict) -> dict:
    """Generate a structured business report from analysis results.

    Args:
        query: The original business question.
        analysis: Combined analysis results from all agents.

    Returns:
        dict with structured report content.
    """
    try:
        root_causes = analysis.get("root_causes", [])
        recommendations = analysis.get("recommendations", [])
        sales = analysis.get("sales_analysis", {})
        inventory = analysis.get("inventory_analysis", {})
        marketing = analysis.get("marketing_analysis", {})
        support = analysis.get("support_analysis", {})
        anomalies = analysis.get("anomalies", {})

        # Executive summary
        summary_lines = [f"## Business Analysis Report", f"**Query:** {query}", ""]

        if sales.get("revenue_change_pct"):
            direction = "decreased" if sales["revenue_change_pct"] < 0 else "increased"
            summary_lines.append(
                f"Revenue {direction} by **{abs(sales['revenue_change_pct']):.1f}%** compared to the previous month."
            )

        if root_causes:
            summary_lines.append(f"\n### Top {min(len(root_causes), 3)} Root Causes:")
            for i, cause in enumerate(root_causes[:3], 1):
                summary_lines.append(
                    f"{i}. **{cause['cause']}** (confidence: {cause['confidence']:.0%})"
                )

        if recommendations:
            summary_lines.append(f"\n### Recommended Actions:")
            for i, rec in enumerate(recommendations[:5], 1):
                action = rec.get("action", rec.get("cause", ""))
                urgency = rec.get("urgency", "medium")
                summary_lines.append(f"{i}. [{urgency.upper()}] {action}")

        # Confidence score
        overall_confidence = root_causes[0]["confidence"] if root_causes else 0
        summary_lines.append(f"\n**Overall Confidence:** {overall_confidence:.0%}")

        # Evidence summary
        evidence_sources = []
        if sales.get("status") == "success":
            evidence_sources.append(f"Sales data ({sales.get('total_orders', 0)} orders)")
        if inventory.get("status") == "success":
            evidence_sources.append(f"Inventory data ({inventory.get('total_products', 0)} products)")
        if marketing.get("status") == "success":
            evidence_sources.append(f"Marketing data ({marketing.get('total_conversions', 0)} conversions)")
        if support.get("status") == "success":
            evidence_sources.append(f"Support data ({support.get('total_tickets', 0)} tickets)")

        summary_lines.append(f"\n**Evidence Sources:** {', '.join(evidence_sources)}")
        summary_lines.append(f"\n*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")

        return {
            "status": "success",
            "executive_summary": "\n".join(summary_lines),
            "query": query,
            "root_causes": root_causes,
            "recommendations": recommendations,
            "sales_summary": {
                "revenue_change_pct": sales.get("revenue_change_pct"),
                "total_revenue": sales.get("total_revenue"),
                "total_orders": sales.get("total_orders"),
            } if sales.get("status") == "success" else None,
            "inventory_summary": {
                "stockout_count": inventory.get("stockout_count"),
                "risk_level": inventory.get("risk_level"),
            } if inventory.get("status") == "success" else None,
            "marketing_summary": {
                "overall_roi": marketing.get("overall_roi"),
                "roi_change": marketing.get("roi_change"),
                "wasted_spend": marketing.get("wasted_spend"),
            } if marketing.get("status") == "success" else None,
            "support_summary": {
                "total_tickets": support.get("total_tickets"),
                "has_spike": support.get("has_complaint_spike"),
                "negative_pct": support.get("negative_sentiment_pct"),
            } if support.get("status") == "success" else None,
            "anomaly_count": anomalies.get("anomaly_count", 0),
            "overall_confidence": overall_confidence,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
