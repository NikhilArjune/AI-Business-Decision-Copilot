"""
AI Business Decision Copilot - Data Tools

These tools handle the first stage of the analysis pipeline: reading and
profiling business datasets. Data quality assessment is critical because
all downstream agent analyses depend on having clean, well-structured data.

Tools:
    read_uploaded_file: Reads CSV/Excel and returns schema info + sample rows
    profile_dataset_tool: Comprehensive quality profiling with statistics

Both tools support CSV and Excel formats, which covers >90% of business
data exports from CRMs, ERPs, and spreadsheet tools.
"""

import pandas as pd
import os
from typing import Optional


def read_uploaded_file(file_path: str) -> dict:
    """Read an uploaded CSV or Excel file and return its structure.

    This is typically the first tool called in the pipeline. It provides
    the Data Agent with schema information (column names, types, row count)
    so it can assess whether the dataset is suitable for analysis.

    The sample_data (first 5 rows) helps the LLM understand the data format
    and make better decisions about which analysis tools to invoke.

    Args:
        file_path: Absolute path to the file to read.

    Returns:
        dict with keys:
            - status: "success" or "error"
            - columns: list of column names
            - row_count: total number of rows
            - dtypes: mapping of column name → data type
            - sample_data: first 5 rows as list of dicts
    """
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"File not found: {file_path}"}

    try:
        # Determine file type and read accordingly
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            return {"status": "error", "message": "Unsupported file type"}

        return {
            "status": "success",
            "file_path": file_path,
            "columns": list(df.columns),
            "row_count": len(df),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            # Return first 5 rows so the LLM can understand data format
            "sample_data": df.head(5).to_dict(orient="records"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def profile_dataset_tool(file_path: str) -> dict:
    """Generate a comprehensive quality profile for a dataset.

    This tool computes a detailed data quality assessment including:
    - Per-column statistics (min, max, mean, std for numeric columns)
    - Missing value analysis (count and percentage per column)
    - Duplicate row detection
    - Overall quality score (0-100) based on data completeness

    The quality score formula:
        score = (1 - total_missing_cells / total_cells) × 100

    Quality grades:
        ≥95 = "Excellent" (minimal data issues)
        ≥80 = "Good" (some gaps but usable)
        ≥60 = "Fair" (significant gaps, results may be affected)
        <60 = "Poor" (unreliable data, analysis should be flagged)

    Args:
        file_path: Path to CSV or Excel file to profile.

    Returns:
        dict with schema info, statistics, quality score, and quality grade.
    """
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Build per-column profile with type info and statistics
        columns_info = []
        for col in df.columns:
            info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null": int(df[col].notna().sum()),
                "null_count": int(df[col].isna().sum()),
                "null_pct": round(df[col].isna().mean() * 100, 1),
                "unique": int(df[col].nunique()),
            }
            # Add statistical summary for numeric columns only
            if df[col].dtype in ["int64", "float64"]:
                info["min"] = float(df[col].min()) if df[col].notna().any() else None
                info["max"] = float(df[col].max()) if df[col].notna().any() else None
                info["mean"] = round(float(df[col].mean()), 2) if df[col].notna().any() else None
                info["std"] = round(float(df[col].std()), 2) if df[col].notna().any() else None
            columns_info.append(info)

        # Calculate overall data quality score (completeness-based)
        total_cells = len(df) * len(df.columns)
        total_missing = sum(df[col].isna().sum() for col in df.columns)
        quality_score = round((1 - total_missing / max(total_cells, 1)) * 100, 1)

        return {
            "status": "success",
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns_info,
            "duplicates": int(df.duplicated().sum()),
            "quality_score": quality_score,
            "quality_grade": "Excellent" if quality_score >= 95 else "Good" if quality_score >= 80 else "Fair" if quality_score >= 60 else "Poor",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
