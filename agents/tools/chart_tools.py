"""
AI Business Decision Copilot - Chart Generation Tools

Produces the visualizations embedded in the final executive report. Charts
are returned as Plotly figure JSON (not images) so the frontend can render
them interactively and keep them consistent with the app's dark theme.

Design notes:
    - Figures are serialized to JSON via fig.to_json() and parsed back into a
      dict so the API can embed them directly in a JSON response — the frontend
      hands this straight to Plotly.js.
    - All charts share the "plotly_dark" template and the app's indigo accent
      (#6366f1) so every visualization in a report reads as one visual system.
    - The Report Agent picks the chart_type that fits each metric: line for
      trends over time, bar for comparisons, pie for composition, grouped_bar
      for multi-series comparisons (e.g. channels across months).
"""

import plotly.graph_objects as go
import plotly.express as px
import json
from typing import Optional


def generate_chart(chart_type: str, data: dict, title: str = "") -> dict:
    """Build a Plotly figure of the requested type and return it as JSON.

    Business Logic:
        Each chart_type maps to the visualization that best communicates a
        particular shape of business data:
            - "line": a metric over time (e.g. monthly revenue trend)
            - "bar": ranked comparison (e.g. revenue by product)
            - "pie": part-to-whole composition (e.g. sentiment split); rendered
              as a donut (hole=0.4) for a cleaner look with a center label
            - "grouped_bar": several series side by side (e.g. spend vs revenue
              per channel)
        Unknown types return an error status rather than raising, so a bad
        request from the LLM degrades gracefully instead of failing the report.

    Args:
        chart_type: One of "line", "bar", "pie", "grouped_bar".
        data: Chart data. Keys used depend on type — line/bar use x/y/name,
            pie uses labels/values, grouped_bar uses a "series" list.
        title: Chart title shown above the plot.

    Returns:
        dict with status and, on success, the Plotly figure as chart_json.
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
            # Unsupported type — fail soft so one bad chart request doesn't
            # abort the whole report generation step.
            return {"status": "error", "message": f"Unknown chart type: {chart_type}"}

        # Shared styling applied to every chart type for a consistent look
        # (tight margins, the app's Inter font) across the report.
        fig.update_layout(
            margin=dict(l=40, r=40, t=60, b=40),
            font=dict(family="Inter, sans-serif", size=12),
        )

        return {
            "status": "success",
            # Round-trip through JSON so the payload is a plain dict the API can
            # embed and Plotly.js can consume directly on the frontend.
            "chart_json": json.loads(fig.to_json()),
            "chart_type": chart_type,
            "title": title,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
