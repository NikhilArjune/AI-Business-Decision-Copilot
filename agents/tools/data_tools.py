"""
AI Business Decision Copilot - Data Tools
Tools for reading and profiling business datasets.
"""

import pandas as pd
import os
from typing import Optional


def read_uploaded_file(file_path: str) -> dict:
    """Read an uploaded CSV or Excel file and return basic info.

    Args:
        file_path: Absolute path to the file.

    Returns:
        dict with columns, row_count, sample_data, and dtypes.
    """
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"File not found: {file_path}"}

    try:
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
            "sample_data": df.head(5).to_dict(orient="records"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def profile_dataset_tool(file_path: str) -> dict:
    """Generate a comprehensive quality profile for a dataset.

    Args:
        file_path: Path to CSV or Excel file.

    Returns:
        dict with schema, missing values, statistics, quality score.
    """
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

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
            if df[col].dtype in ["int64", "float64"]:
                info["min"] = float(df[col].min()) if df[col].notna().any() else None
                info["max"] = float(df[col].max()) if df[col].notna().any() else None
                info["mean"] = round(float(df[col].mean()), 2) if df[col].notna().any() else None
                info["std"] = round(float(df[col].std()), 2) if df[col].notna().any() else None
            columns_info.append(info)

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
