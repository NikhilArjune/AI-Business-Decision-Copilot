"""
AI Business Decision Copilot - Pydantic Schemas for API Request/Response
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime


# =============================================================================
# Auth Schemas
# =============================================================================

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(default="analyst", pattern="^(admin|manager|analyst|viewer)$")


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# =============================================================================
# Dataset Schemas
# =============================================================================

class DatasetResponse(BaseModel):
    id: str
    name: str
    file_type: str
    file_size: Optional[int] = None
    schema_info: Optional[dict] = None
    row_count: Optional[int] = None
    quality_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetProfileResponse(BaseModel):
    columns: List[dict]
    row_count: int
    missing_values: dict
    duplicates: int
    statistics: dict
    quality_score: float


# =============================================================================
# Copilot Schemas
# =============================================================================

class CopilotQuery(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000)
    dataset_ids: Optional[List[str]] = None


class AgentStepResponse(BaseModel):
    agent_name: str
    status: str
    execution_time_ms: Optional[int] = None
    output_summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CopilotRunResponse(BaseModel):
    id: str
    query: str
    status: str
    final_answer: Optional[dict] = None
    root_causes: Optional[list] = None
    recommendations: Optional[list] = None
    confidence_score: Optional[float] = None
    steps: List[AgentStepResponse] = []
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# Report Schemas
# =============================================================================

class ReportResponse(BaseModel):
    id: str
    run_id: str
    title: str
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Audit Schemas
# =============================================================================

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True
