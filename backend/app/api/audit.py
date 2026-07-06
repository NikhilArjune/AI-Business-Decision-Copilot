"""
AI Business Decision Copilot - Audit Log API
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..database import get_db
from ..models.db_models import AuditLog
from ..schemas.api_schemas import AuditLogResponse
from ..core.security import require_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    limit: int = 100,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get audit logs (admin only)."""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    return result.scalars().all()
