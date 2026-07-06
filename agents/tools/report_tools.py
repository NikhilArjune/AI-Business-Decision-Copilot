"""
AI Business Decision Copilot - Report Generation Tools

Assembles every stage of the pipeline into the final executive deliverable —
the artifact a business owner or board actually reads. It deliberately leads
with the answer (revenue direction, top causes, recommended actions) and
follows with the evidence, because decision-makers want the "so what?" first.

Structure produced:
    - A Markdown executive summary (headline metric → top 3 causes →
      recommended actions → overall confidence → evidence sources)
    - Compact per-domain summaries, included only for domains that ran
      successfully, so the report never shows empty or misleading sections
    - Provenance: the datasets analyzed and a generation timestamp, so every
      report is auditable and reproducible
"""

import json
from datetime import datetime, timezone
from typing import Optional


def generate_report(query: str, analysis: dict) -> dict:
    """Compile all analysis results into a structured executive report.

    Business Logic:
        - The executive summary is built as Markdown so it renders cleanly in
          the frontend. It opens with revenue direction (the number the owner
          cares about most), then the top 3 root causes with their confidence,
          then the top 5 recommended actions tagged by urgency.
        - Overall confidence is taken from the highest-ranked root cause — it
          represents how sure we are of the leading explanation.
        - Per-domain summaries are conditional on status == "success": a domain
          that failed or had no data is simply omitted rather than shown as
          zeros, keeping the report honest.
        - Evidence sources list the datasets (and their sizes) that backed the
          analysis, making the conclusions traceable.

    Args:
        query: The original business question asked by the user.
        analysis: Combined results from all pipeline stages (root_causes,
            recommendations, and each "<domain>_analysis" block).

    Returns:
        dict with the Markdown executive_summary, structured causes and
        recommendations, per-domain summaries, and generation metadata.
    """
    try:
        root_causes = analysis.get("root_causes", [])
        recommendations = analysis.get("recommendations", [])
        sales = analysis.get("sales_analysis", {})
        inventory = analysis.get("inventory_analysis", {})
        marketing = analysis.get("marketing_analysis", {})
        support = analysis.get("support_analysis", {})
        anomalies = analysis.get("anomalies", {})

        # ── Executive summary (Markdown) ─────────────────────────────
        # Assembled line by line, leading with the headline revenue metric so
        # the reader gets the bottom line before the supporting detail.
        summary_lines = [f"## Business Analysis Report", f"**Query:** {query}", ""]

        # Headline: which way did revenue move, and by how much?
        if sales.get("revenue_change_pct"):
            direction = "decreased" if sales["revenue_change_pct"] < 0 else "increased"
            summary_lines.append(
                f"Revenue {direction} by **{abs(sales['revenue_change_pct']):.1f}%** compared to the previous month."
            )

        # The three most likely explanations, each with its confidence.
        if root_causes:
            summary_lines.append(f"\n### Top {min(len(root_causes), 3)} Root Causes:")
            for i, cause in enumerate(root_causes[:3], 1):
                summary_lines.append(
                    f"{i}. **{cause['cause']}** (confidence: {cause['confidence']:.0%})"
                )

        # The top five actions, urgency-tagged so the reader can triage.
        if recommendations:
            summary_lines.append(f"\n### Recommended Actions:")
            for i, rec in enumerate(recommendations[:5], 1):
                action = rec.get("action", rec.get("cause", ""))
                urgency = rec.get("urgency", "medium")
                summary_lines.append(f"{i}. [{urgency.upper()}] {action}")

        # Overall confidence = the leading cause's confidence (0 if none found).
        overall_confidence = root_causes[0]["confidence"] if root_causes else 0
        summary_lines.append(f"\n**Overall Confidence:** {overall_confidence:.0%}")

        # ── Evidence sources ─────────────────────────────────────────
        # List only the domains that actually contributed data, with a size
        # figure each, so the conclusions are traceable to real inputs.
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
            # Per-domain summaries are emitted only when that domain ran
            # successfully (None otherwise), so the report never fabricates
            # zeros for a domain that had no data.
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
