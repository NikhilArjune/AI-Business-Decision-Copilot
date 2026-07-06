"""
AI Business Decision Copilot - Dataset Upload & Profiling API
"""

import os
import logging
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..database import get_db
from ..models.db_models import Dataset, AuditLog
from ..schemas.api_schemas import DatasetResponse, DatasetProfileResponse
from ..core.security import get_current_user, require_role
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/datasets", tags=["Datasets"])

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def _profile_dataframe(df: pd.DataFrame) -> dict:
    """Generate profiling info for a dataframe."""
    columns = []
    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].notna().sum()),
            "null_count": int(df[col].isna().sum()),
            "unique": int(df[col].nunique()),
        }
        if df[col].dtype in ["int64", "float64"]:
            col_info["min"] = float(df[col].min()) if df[col].notna().any() else None
            col_info["max"] = float(df[col].max()) if df[col].notna().any() else None
            col_info["mean"] = float(df[col].mean()) if df[col].notna().any() else None
        columns.append(col_info)

    missing_values = {col: int(df[col].isna().sum()) for col in df.columns}
    total_cells = len(df) * len(df.columns)
    total_missing = sum(missing_values.values())
    quality_score = round((1 - total_missing / max(total_cells, 1)) * 100, 1)

    stats = {}
    numeric_cols = df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        stats[col] = {
            "mean": round(float(df[col].mean()), 2) if df[col].notna().any() else None,
            "std": round(float(df[col].std()), 2) if df[col].notna().any() else None,
            "min": round(float(df[col].min()), 2) if df[col].notna().any() else None,
            "max": round(float(df[col].max()), 2) if df[col].notna().any() else None,
        }

    return {
        "columns": columns,
        "row_count": len(df),
        "missing_values": missing_values,
        "duplicates": int(df.duplicated().sum()),
        "statistics": stats,
        "quality_score": quality_score,
    }


@router.post("/upload", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV or Excel file."""
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}")

    # Validate size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(400, f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB}MB")

    # Save file
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    import uuid
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # Profile the dataset
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        profile = _profile_dataframe(df)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    # Save to database
    dataset = Dataset(
        name=file.filename,
        file_type=ext.lstrip("."),
        file_path=file_path,
        file_size=len(content),
        schema_info={"columns": profile["columns"]},
        row_count=profile["row_count"],
        quality_score=profile["quality_score"],
        uploaded_by=current_user["user_id"],
    )
    db.add(dataset)
    db.add(AuditLog(
        user_id=current_user["user_id"],
        action="dataset_uploaded",
        resource_type="dataset",
        resource_id=dataset.id,
        details={"filename": file.filename, "rows": profile["row_count"]},
    ))
    await db.flush()

    logger.info(f"Dataset uploaded: {file.filename} ({profile['row_count']} rows)")
    return dataset


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all datasets."""
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return result.scalars().all()


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
async def get_dataset_profile(
    dataset_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed profiling for a dataset."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(404, "Dataset not found")

    try:
        if dataset.file_type == "csv":
            df = pd.read_csv(dataset.file_path)
        else:
            df = pd.read_excel(dataset.file_path)
        return _profile_dataframe(df)
    except Exception as e:
        raise HTTPException(500, f"Failed to profile dataset: {str(e)}")
