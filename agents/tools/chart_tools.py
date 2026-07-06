"""
AI Business Decision Copilot - Chart Generation Tools
"""

import plotly.graph_objects as go
import plotly.express as px
import json
from typing import Optional


def generate_chart(chart_type: str, data: dict, title: str = "") -> dict:
    """Generate a Plotly chart and return it as JSON.

    Args:
        chart_type: Type of chart (line, bar, pie, heatmap).
        data: Chart data with x, y, labels, etc.
        title: Chart title.

    Returns:
        dict with Plotly chart JSON.
    """
    try:
        if chart_type == "line":
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=data.get("x", []),
                y=data.get("y", []),
                mode="lines+markers",
                name=data.get("name", "Value"),
                line=dict(color="#6366f1", width=2),
                marker=dict(size=6),
            ))
            fig.update_layout(title=title, template="plotly_dark")

        elif chart_type == "bar":
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=data.get("x", []),
                y=data.get("y", []),
                name=data.get("name", "Value"),
                marker_color=data.get("colors", "#6366f1"),
            ))
            fig.update_layout(title=title, template="plotly_dark")

        elif chart_type == "pie":
            fig = go.Figure()
            fig.add_trace(go.Pie(
                labels=data.get("labels", []),
                values=data.get("values", []),
                hole=0.4,
            ))
            fig.update_layout(title=title, template="plotly_dark")

        elif chart_type == "grouped_bar":
            fig = go.Figure()
            for series in data.get("series", []):
                fig.add_trace(go.Bar(
                    x=series.get("x", []),
                    y=series.get("y", []),
                    name=series.get("name", ""),
                ))
            fig.update_layout(title=title, barmode="group", template="plotly_dark")

        else:
            return {"status": "error", "message": f"Unknown chart type: {chart_type}"}

        fig.update_layout(
            margin=dict(l=40, r=40, t=60, b=40),
            font=dict(family="Inter, sans-serif", size=12),
        )

        return {
            "status": "success",
            "chart_json": json.loads(fig.to_json()),
            "chart_type": chart_type,
            "title": title,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
