"""
AI Business Decision Copilot - SQLAlchemy Models
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from ..database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="analyst")  # admin, manager, analyst, viewer
    created_at = Column(DateTime, default=utcnow)

    agent_runs = relationship("AgentRun", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # csv, xlsx
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    schema_info = Column(JSON, nullable=True)
    row_count = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    query = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    final_answer = Column(JSON, nullable=True)
    root_causes = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    started_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="agent_runs")
    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="run", cascade="all, delete-orphan")


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(20), default="running")  # running, completed, failed
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    run = relationship("AgentRun", back_populates="steps")
    tool_calls = relationship("ToolCall", back_populates="step", cascade="all, delete-orphan")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(String, primary_key=True, default=generate_uuid)
    step_id = Column(String, ForeignKey("agent_steps.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    approved = Column(Boolean, default=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    step = relationship("AgentStep", back_populates="tool_calls")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    metadata_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    run = relationship("AgentRun", back_populates="reports")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="audit_logs")
