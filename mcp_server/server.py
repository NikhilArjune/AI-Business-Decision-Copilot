"""
AI Business Decision Copilot - MCP Server
Exposes business analysis tools to ADK agents via the Model Context Protocol.
"""

import os
import sys
import json
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from mcp.server.fastmcp import FastMCP

from agents.tools.data_tools import read_uploaded_file, profile_dataset_tool
from agents.tools.sales_tools import run_sales_analysis
from agents.tools.inventory_tools import run_inventory_analysis
from agents.tools.marketing_tools import run_marketing_analysis
from agents.tools.support_tools import run_support_analysis
from agents.tools.analytics_tools import run_anomaly_detection
from agents.tools.chart_tools import generate_chart
from agents.tools.report_tools import generate_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP(
    "AI Business Decision Copilot MCP Server",
    description="Business analysis tools for the AI Business Decision Copilot",
)

# Default data directory
DATA_DIR = os.path.join(project_root, "data")


@mcp.tool()
def read_file(file_path: str) -> str:
    """Read a CSV or Excel business data file and return its structure.

    Args:
        file_path: Path to the file to read. Use filenames from the data directory.
    """
    # Resolve relative paths to data directory
    if not os.path.isabs(file_path):
        file_path = os.path.join(DATA_DIR, file_path)
    result = read_uploaded_file(file_path)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def profile_dataset(file_path: str) -> str:
    """Generate a comprehensive quality profile for a business dataset.

    Args:
        file_path: Path to the CSV or Excel file to profile.
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(DATA_DIR, file_path)
    result = profile_dataset_tool(file_path)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def analyze_sales(file_path: str = "sample_sales.csv") -> str:
    """Analyze sales data: revenue trends, product performance, regional breakdown.

    Args:
        file_path: Path to sales CSV file.
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(DATA_DIR, file_path)
    import pandas as pd
    df = pd.read_csv(file_path)
    result = run_sales_analysis(df)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def analyze_inventory(file_path: str = "sample_inventory.csv") -> str:
    """Analyze inventory: detect stockouts, low stock, blocked inventory.

    Args:
        file_path: Path to inventory CSV file.
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(DATA_DIR, file_path)
    import pandas as pd
    df = pd.read_csv(file_path)
    result = run_inventory_analysis(df)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def analyze_marketing(file_path: str = "sample_marketing.csv") -> str:
    """Analyze marketing campaigns: ROI, conversion rates, channel performance.

    Args:
        file_path: Path to marketing CSV file.
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(DATA_DIR, file_path)
    import pandas as pd
    df = pd.read_csv(file_path)
    result = run_marketing_analysis(df)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def analyze_support(file_path: str = "sample_support_tickets.csv") -> str:
    """Analyze customer support tickets: complaints, sentiment, ticket spikes.

    Args:
        file_path: Path to support tickets CSV file.
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(DATA_DIR, file_path)
    import pandas as pd
    df = pd.read_csv(file_path)
    result = run_support_analysis(df)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def detect_anomalies(file_path: str = "sample_sales.csv") -> str:
    """Detect statistical anomalies in sales data using Z-score analysis.

    Args:
        file_path: Path to sales CSV file.
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(DATA_DIR, file_path)
    import pandas as pd
    df = pd.read_csv(file_path)
    result = run_anomaly_detection(df)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def create_chart(chart_type: str, title: str, x_values: str, y_values: str) -> str:
    """Generate a Plotly chart from data.

    Args:
        chart_type: Type of chart (line, bar, pie).
        title: Chart title.
        x_values: Comma-separated X-axis values.
        y_values: Comma-separated Y-axis values.
    """
    data = {
        "x": x_values.split(","),
        "y": [float(v.strip()) for v in y_values.split(",")],
    }
    result = generate_chart(chart_type, data, title)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def list_datasets() -> str:
    """List all available business datasets in the data directory."""
    files = []
    if os.path.exists(DATA_DIR):
        for f in sorted(os.listdir(DATA_DIR)):
            if f.endswith((".csv", ".xlsx")):
                path = os.path.join(DATA_DIR, f)
                size = os.path.getsize(path)
                files.append({"name": f, "path": path, "size_bytes": size})
    return json.dumps({"datasets": files}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
