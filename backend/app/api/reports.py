"""
AI Business Decision Copilot - Reports API
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..database import get_db
from ..models.db_models import Report
from ..schemas.api_schemas import ReportResponse
from ..core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all generated reports."""
    result = await db.execute(select(Report).order_by(Report.created_at.desc()))
    return result.scalars().all()


@router.get("/{run_id}", response_model=ReportResponse)
async def get_report(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get report for a specific run."""
    result = await db.execute(select(Report).where(Report.run_id == run_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    return report


@router.get("/{run_id}/html")
async def get_report_html(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the HTML content of a report."""
    result = await db.execute(select(Report).where(Report.run_id == run_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    return HTMLResponse(content=report.html_content or "<p>No content</p>")
