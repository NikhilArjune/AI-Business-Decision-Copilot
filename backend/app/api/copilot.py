"""
AI Business Decision Copilot - Copilot Query API (triggers the agent pipeline)
"""

import os
import logging
import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.db_models import AgentRun, AgentStep, ToolCall, AuditLog, Dataset, Report
from ..schemas.api_schemas import CopilotQuery, CopilotRunResponse, AgentStepResponse
from ..core.security import get_current_user
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/copilot", tags=["Copilot"])


async def _run_agent_pipeline(run_id: str, query: str, dataset_paths: list):
    """
    Execute the ADK multi-agent pipeline in the background.
    This imports and runs the agent system, recording steps to the database.
    """
    from ..database import async_session
    import pandas as pd

    async with async_session() as db:
        try:
            # Update status to running
            result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = "running"
            await db.commit()

            # Load datasets
            all_data = {}
            for path in dataset_paths:
                name = os.path.splitext(os.path.basename(path))[0]
                try:
                    if path.endswith(".csv"):
                        all_data[name] = pd.read_csv(path)
                    else:
                        all_data[name] = pd.read_excel(path)
                except Exception as e:
                    logger.warning(f"Failed to load {path}: {e}")

            # Import analytics tools and run analysis
            from agents.tools.data_tools import profile_dataset_tool
            from agents.tools.sales_tools import run_sales_analysis
            from agents.tools.inventory_tools import run_inventory_analysis
            from agents.tools.marketing_tools import run_marketing_analysis
            from agents.tools.support_tools import run_support_analysis
            from agents.tools.analytics_tools import run_anomaly_detection, run_root_cause_ranking

            results = {}
            agents_sequence = [
                ("Data Agent", "data_profiling", lambda: _run_data_agent(all_data)),
                ("Sales Agent", "sales_analysis", lambda: run_sales_analysis(all_data.get("sample_sales"))),
                ("Inventory Agent", "inventory_analysis", lambda: run_inventory_analysis(all_data.get("sample_inventory"))),
                ("Marketing Agent", "marketing_analysis", lambda: run_marketing_analysis(all_data.get("sample_marketing"))),
                ("Support Agent", "support_analysis", lambda: run_support_analysis(all_data.get("sample_support_tickets"))),
            ]

            for agent_name, key, func in agents_sequence:
                step_start = time.time()
                step = AgentStep(
                    run_id=run_id,
                    agent_name=agent_name,
                    status="running",
                )
                db.add(step)
                await db.flush()

                try:
                    result_data = func()
                    results[key] = result_data
                    step.status = "completed"
                    step.output_data = _safe_json(result_data)
                    step.execution_time_ms = int((time.time() - step_start) * 1000)
                except Exception as e:
                    step.status = "failed"
                    step.output_data = {"error": str(e)}
                    logger.error(f"{agent_name} failed: {e}")

                await db.commit()

            # Analytics Agent - anomaly detection & root cause
            step_start = time.time()
            step = AgentStep(run_id=run_id, agent_name="Analytics Agent", status="running")
            db.add(step)
            await db.flush()

            try:
                anomalies = run_anomaly_detection(all_data.get("sample_sales"))
                root_causes = run_root_cause_ranking(results)
                results["anomalies"] = anomalies
                results["root_causes"] = root_causes
                step.status = "completed"
                step.output_data = _safe_json({"anomalies": anomalies, "root_causes": root_causes})
                step.execution_time_ms = int((time.time() - step_start) * 1000)
            except Exception as e:
                step.status = "failed"
                step.output_data = {"error": str(e)}
            await db.commit()

            # Generate recommendations
            step_start = time.time()
            step = AgentStep(run_id=run_id, agent_name="Recommendation Agent", status="running")
            db.add(step)
            await db.flush()

            try:
                recommendations = _generate_recommendations(results)
                results["recommendations"] = recommendations
                step.status = "completed"
                step.output_data = _safe_json({"recommendations": recommendations})
                step.execution_time_ms = int((time.time() - step_start) * 1000)
            except Exception as e:
                step.status = "failed"
                step.output_data = {"error": str(e)}
            await db.commit()

            # Generate report
            step_start = time.time()
            step = AgentStep(run_id=run_id, agent_name="Report Agent", status="running")
            db.add(step)
            await db.flush()

            try:
                report_content = _generate_report_content(query, results)
                report = Report(
                    run_id=run_id,
                    title=f"Business Analysis: {query[:100]}",
                    summary=report_content.get("executive_summary", ""),
                    html_content=json.dumps(report_content),
                )
                db.add(report)
                step.status = "completed"
                step.output_data = {"report_generated": True}
                step.execution_time_ms = int((time.time() - step_start) * 1000)
            except Exception as e:
                step.status = "failed"
                step.output_data = {"error": str(e)}
            await db.commit()

            # Update run with final results
            result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = "completed"
            run.final_answer = _safe_json(report_content) if 'report_content' in dir() else {"error": "Report generation failed"}
            run.root_causes = _safe_json(results.get("root_causes", []))
            run.recommendations = _safe_json(results.get("recommendations", []))
            run.confidence_score = results.get("root_causes", [{}])[0].get("confidence", 0.0) if results.get("root_causes") else 0.0
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Agent pipeline completed for run {run_id}")

        except Exception as e:
            logger.error(f"Pipeline failed for run {run_id}: {e}", exc_info=True)
            result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = "failed"
            run.final_answer = {"error": str(e)}
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()


def _run_data_agent(all_data: dict) -> dict:
    """Profile all loaded datasets."""
    profiles = {}
    for name, df in all_data.items():
        profiles[name] = {
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing": {col: int(df[col].isna().sum()) for col in df.columns},
        }
    return profiles


def _generate_recommendations(results: dict) -> list:
    """Generate recommendations from analysis results."""
    recs = []
    root_causes = results.get("root_causes", [])

    for i, cause in enumerate(root_causes[:5]):
        rec = {
            "priority": i + 1,
            "action": cause.get("recommendation", f"Address: {cause.get('cause', 'Unknown issue')}"),
            "urgency": "high" if cause.get("confidence", 0) > 0.7 else "medium",
            "impact": cause.get("impact", "moderate"),
            "evidence": cause.get("evidence", ""),
        }
        recs.append(rec)

    return recs


def _generate_report_content(query: str, results: dict) -> dict:
    """Generate structured report content."""
    root_causes = results.get("root_causes", [])
    recommendations = results.get("recommendations", [])
    sales = results.get("sales_analysis", {})
    anomalies = results.get("anomalies", {})

    summary_parts = []
    if sales.get("revenue_change_pct"):
        summary_parts.append(f"Revenue changed by {sales['revenue_change_pct']:.1f}% compared to the previous month.")
    if root_causes:
        summary_parts.append(f"Top {len(root_causes)} root causes identified:")
        for i, cause in enumerate(root_causes[:3], 1):
            summary_parts.append(f"  {i}. {cause.get('cause', 'Unknown')} (confidence: {cause.get('confidence', 0):.0%})")

    return {
        "executive_summary": "\n".join(summary_parts) if summary_parts else "Analysis completed.",
        "query": query,
        "sales_analysis": _safe_json(sales),
        "root_causes": _safe_json(root_causes),
        "recommendations": _safe_json(recommendations),
        "anomalies": _safe_json(anomalies),
        "confidence_score": root_causes[0].get("confidence", 0.0) if root_causes else 0.0,
    }


def _safe_json(obj):
    """Convert object to JSON-safe format."""
    if obj is None:
        return None
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


@router.post("/query", response_model=CopilotRunResponse, status_code=201)
async def create_query(
    data: CopilotQuery,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a business question for analysis."""
    # Get dataset paths
    dataset_paths = []
    if data.dataset_ids:
        for did in data.dataset_ids:
            result = await db.execute(select(Dataset).where(Dataset.id == did))
            ds = result.scalar_one_or_none()
            if ds:
                dataset_paths.append(ds.file_path)
    else:
        # Use all available datasets
        result = await db.execute(select(Dataset))
        datasets = result.scalars().all()
        dataset_paths = [ds.file_path for ds in datasets]

    # If no uploaded datasets, use sample data
    if not dataset_paths:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                if f.endswith((".csv", ".xlsx")):
                    dataset_paths.append(os.path.join(data_dir, f))

    # Create run
    run = AgentRun(
        user_id=current_user["user_id"],
        query=data.query,
        status="pending",
    )
    db.add(run)
    db.add(AuditLog(
        user_id=current_user["user_id"],
        action="copilot_query",
        resource_type="agent_run",
        resource_id=run.id,
        details={"query": data.query},
    ))
    await db.flush()

    # Start pipeline in background
    background_tasks.add_task(_run_agent_pipeline, run.id, data.query, dataset_paths)

    logger.info(f"Copilot query submitted: {data.query[:100]}")
    return CopilotRunResponse(
        id=run.id,
        query=run.query,
        status=run.status,
        started_at=run.started_at,
    )


@router.get("/runs/{run_id}", response_model=CopilotRunResponse)
async def get_run(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the status and results of a copilot run."""
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")

    steps = [
        AgentStepResponse(
            agent_name=s.agent_name,
            status=s.status,
            execution_time_ms=s.execution_time_ms,
            output_summary=str(s.output_data)[:200] if s.output_data else None,
            created_at=s.created_at,
        )
        for s in sorted(run.steps, key=lambda x: x.created_at)
    ]

    return CopilotRunResponse(
        id=run.id,
        query=run.query,
        status=run.status,
        final_answer=run.final_answer,
        root_causes=run.root_causes,
        recommendations=run.recommendations,
        confidence_score=run.confidence_score,
        steps=steps,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )
