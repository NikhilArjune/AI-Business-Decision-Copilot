"""
AI Business Decision Copilot - Copilot Query API

This module implements the core API endpoint that triggers the multi-agent
analysis pipeline. When a user asks a business question (e.g., "Why did
revenue decrease this month?"), this module:

1. Resolves which datasets to analyze (user-uploaded or sample data)
2. Creates an AgentRun record in the database for tracking
3. Logs the action to the audit trail for security compliance
4. Launches the agent pipeline as a background task (non-blocking)
5. Returns immediately with a run_id the frontend can poll for results

PIPELINE ARCHITECTURE:
    The pipeline mirrors the ADK agent structure defined in agents/agent.py,
    but executes the tools directly (without LLM calls) for the backend's
    synchronous analysis path. The ADK agents are used for the interactive
    chat flow, while this pipeline handles the batch analysis workflow.

    Execution order:
        Data Agent → [Sales | Inventory | Marketing | Support] → Analytics
        → Recommendation → Report

    Each step is recorded as an AgentStep in the database with:
        - Agent name, status (running/completed/failed)
        - Execution time in milliseconds (for performance monitoring)
        - Output data (JSON) for debugging and result retrieval
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
    """Execute the multi-agent analysis pipeline as a background task.

    This is the core orchestration function that runs the entire business
    analysis workflow. It's designed to run asynchronously so the API
    endpoint can return immediately while analysis proceeds in the background.

    The pipeline follows a 4-stage approach:
        Stage 1: Load and profile all datasets (Data Agent)
        Stage 2: Run domain-specific analyses (Sales, Inventory, Marketing, Support)
        Stage 3: Detect anomalies and rank root causes (Analytics Agent)
        Stage 4: Generate recommendations and compile the final report

    Each stage creates an AgentStep record in the database, allowing the
    frontend to display real-time progress as agents complete their work.

    Args:
        run_id: UUID of the AgentRun record to update with results.
        query: The user's natural-language business question.
        dataset_paths: List of file paths to the datasets to analyze.

    Error Handling:
        - Individual agent failures are caught and logged but don't stop the pipeline.
        - If the entire pipeline fails, the run status is set to 'failed'.
        - All errors are recorded in the AgentStep output_data for debugging.
    """
    from ..database import async_session
    import pandas as pd

    async with async_session() as db:
        try:
            # ── Stage 0: Mark the run as active ──────────────────────────
            result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = "running"
            await db.commit()

            # ── Stage 1: Load all datasets into memory ───────────────────
            # We load datasets once and pass DataFrames to each agent tool,
            # avoiding redundant file I/O across multiple agents.
            # The dict key is the filename without extension (e.g., "sample_sales"),
            # which matches the expected keys in each analysis tool.
            all_data = {}
            for path in dataset_paths:
                name = os.path.splitext(os.path.basename(path))[0]
                try:
                    if path.endswith(".csv"):
                        all_data[name] = pd.read_csv(path)
                    else:
                        all_data[name] = pd.read_excel(path)
                except Exception as e:
                    # Non-fatal: skip unreadable files, log warning, continue
                    logger.warning(f"Failed to load {path}: {e}")

            # Import analysis tools — deferred import to avoid circular
            # dependencies since agents/ and backend/ are separate packages
            from agents.tools.data_tools import profile_dataset_tool
            from agents.tools.sales_tools import run_sales_analysis
            from agents.tools.inventory_tools import run_inventory_analysis
            from agents.tools.marketing_tools import run_marketing_analysis
            from agents.tools.support_tools import run_support_analysis
            from agents.tools.analytics_tools import run_anomaly_detection, run_root_cause_ranking

            # ── Stage 2: Run domain-specific analyses ────────────────────
            # Each tuple defines: (display_name, results_key, callable)
            # The results_key is used to store output in the results dict,
            # which is later consumed by the Analytics Agent for cross-domain
            # root cause ranking.
            results = {}
            agents_sequence = [
                ("Data Agent", "data_profiling", lambda: _run_data_agent(all_data)),
                ("Sales Agent", "sales_analysis", lambda: run_sales_analysis(all_data.get("sample_sales"))),
                ("Inventory Agent", "inventory_analysis", lambda: run_inventory_analysis(all_data.get("sample_inventory"))),
                ("Marketing Agent", "marketing_analysis", lambda: run_marketing_analysis(all_data.get("sample_marketing"))),
                ("Support Agent", "support_analysis", lambda: run_support_analysis(all_data.get("sample_support_tickets"))),
            ]

            # Execute each agent, recording timing and status to the database.
            # Each agent gets its own AgentStep record for frontend progress tracking.
            for agent_name, key, func in agents_sequence:
                step_start = time.time()
                step = AgentStep(
                    run_id=run_id,
                    agent_name=agent_name,
                    status="running",
                )
                db.add(step)
                await db.flush()  # Flush to assign step ID before execution

                try:
                    result_data = func()
                    results[key] = result_data
                    step.status = "completed"
                    step.output_data = _safe_json(result_data)
                    step.execution_time_ms = int((time.time() - step_start) * 1000)
                except Exception as e:
                    # Agent failure is non-fatal — we continue with other agents.
                    # The Analytics Agent will work with whatever results are available.
                    step.status = "failed"
                    step.output_data = {"error": str(e)}
                    logger.error(f"{agent_name} failed: {e}")

                await db.commit()

            # ── Stage 3: Analytics — anomaly detection & root cause ranking ─
            # This is the synthesis stage where we combine signals from all
            # domain agents to identify the most probable root causes.
            # run_anomaly_detection uses Z-score analysis on sales data.
            # run_root_cause_ranking combines all agent outputs and ranks
            # causes by confidence score (0-1).
            step_start = time.time()
            step = AgentStep(run_id=run_id, agent_name="Analytics Agent", status="running")
            db.add(step)
            await db.flush()

            try:
                # Z-score anomaly detection on daily and monthly revenue
                anomalies = run_anomaly_detection(all_data.get("sample_sales"))
                # Cross-domain root cause ranking — combines sales, inventory,
                # marketing, and support signals into a confidence-scored list
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

            # ── Stage 4a: Generate prioritized recommendations ───────────
            # Converts root causes into actionable business decisions.
            # Higher-confidence causes get higher urgency ratings.
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

            # ── Stage 4b: Compile the final executive report ─────────────
            # Assembles all findings into a structured report with executive
            # summary, root causes, and recommended actions. The report is
            # stored as a separate Report record linked to this run.
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

            # ── Finalize: Update the AgentRun with all results ───────────
            # The run record stores the complete output for the frontend
            # to display: final answer, root causes, recommendations, and
            # the overall confidence score (taken from the top root cause).
            result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = "completed"
            run.final_answer = _safe_json(report_content) if 'report_content' in dir() else {"error": "Report generation failed"}
            run.root_causes = _safe_json(results.get("root_causes", []))
            run.recommendations = _safe_json(results.get("recommendations", []))
            # Confidence score = top root cause's confidence (highest ranked)
            run.confidence_score = results.get("root_causes", [{}])[0].get("confidence", 0.0) if results.get("root_causes") else 0.0
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Agent pipeline completed for run {run_id}")

        except Exception as e:
            # ── Global failure handler ───────────────────────────────────
            # If the entire pipeline crashes (not just individual agents),
            # mark the run as failed and store the error for debugging.
            logger.error(f"Pipeline failed for run {run_id}: {e}", exc_info=True)
            result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = "failed"
            run.final_answer = {"error": str(e)}
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()


def _run_data_agent(all_data: dict) -> dict:
    """Profile all loaded datasets — the Data Agent's core logic.

    Creates a quick schema summary for each dataset including row count,
    column names, data types, and missing value counts. This lightweight
    profiling runs before full analysis to ensure data quality.

    Args:
        all_data: Dict mapping dataset names to pandas DataFrames.

    Returns:
        Dict of dataset profiles keyed by dataset name.
    """
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
    """Convert root causes into prioritized, actionable recommendations.

    Business Logic:
        - Takes the top 5 root causes (already ranked by confidence)
        - Assigns urgency based on confidence score:
            > 0.7 confidence → "high" urgency (act immediately)
            ≤ 0.7 confidence → "medium" urgency (investigate further)
        - Each recommendation includes the evidence that supports it,
          maintaining the evidence chain from analysis to action

    Args:
        results: Combined analysis results containing 'root_causes' list.

    Returns:
        List of recommendation dicts with priority, action, urgency, impact, evidence.
    """
    recs = []
    root_causes = results.get("root_causes", [])

    for i, cause in enumerate(root_causes[:5]):
        rec = {
            "priority": i + 1,
            "action": cause.get("recommendation", f"Address: {cause.get('cause', 'Unknown issue')}"),
            # Urgency threshold: 0.7 confidence = high urgency
            "urgency": "high" if cause.get("confidence", 0) > 0.7 else "medium",
            "impact": cause.get("impact", "moderate"),
            "evidence": cause.get("evidence", ""),
        }
        recs.append(rec)

    return recs


def _generate_report_content(query: str, results: dict) -> dict:
    """Compile all analysis results into a structured executive report.

    Produces a report with:
        - Executive summary with revenue change and top root causes
        - Full root cause list with confidence scores
        - Prioritized recommendations
        - Anomaly detection results
        - Overall confidence score (from top root cause)

    The report is stored as JSON and can be rendered as HTML by the
    /reports/{run_id}/html endpoint.

    Args:
        query: The original business question asked by the user.
        results: Complete analysis results from all pipeline stages.

    Returns:
        Dict containing structured report content.
    """
    root_causes = results.get("root_causes", [])
    recommendations = results.get("recommendations", [])
    sales = results.get("sales_analysis", {})
    anomalies = results.get("anomalies", {})

    # Build executive summary — the first thing a business owner reads
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
    """Safely convert any Python object to a JSON-serializable format.

    Some analysis tools return numpy types (np.int64, np.float64) or
    pandas objects that aren't JSON-serializable. This function catches
    serialization failures and falls back to string representation.

    Args:
        obj: Any Python object to make JSON-safe.

    Returns:
        The original object if JSON-serializable, or str(obj) as fallback.
    """
    if obj is None:
        return None
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/query", response_model=CopilotRunResponse, status_code=201)
async def create_query(
    data: CopilotQuery,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a business question for multi-agent analysis.

    This endpoint accepts a natural-language business question and triggers
    the full agent pipeline in the background. The response returns immediately
    with a run_id that the frontend can poll via GET /copilot/runs/{run_id}.

    Dataset Resolution Strategy:
        1. If specific dataset_ids are provided, use those datasets
        2. If no IDs provided, use ALL uploaded datasets
        3. If no uploaded datasets exist, fall back to sample data in /data/

    Security:
        - Requires JWT authentication (any role can query)
        - Every query is logged to the audit trail with user_id and query text
    """
    # ── Resolve which datasets to analyze ────────────────────────────
    dataset_paths = []
    if data.dataset_ids:
        # User specified specific datasets — fetch their file paths
        for did in data.dataset_ids:
            result = await db.execute(select(Dataset).where(Dataset.id == did))
            ds = result.scalar_one_or_none()
            if ds:
                dataset_paths.append(ds.file_path)
    else:
        # No specific datasets requested — use all available uploaded datasets
        result = await db.execute(select(Dataset))
        datasets = result.scalars().all()
        dataset_paths = [ds.file_path for ds in datasets]

    # ── Fallback: use bundled sample data if no uploads exist ────────
    # This ensures the demo works out-of-the-box without requiring
    # the user to upload files first.
    if not dataset_paths:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                if f.endswith((".csv", ".xlsx")):
                    dataset_paths.append(os.path.join(data_dir, f))

    # ── Create the AgentRun record ───────────────────────────────────
    # This record tracks the entire analysis lifecycle: pending → running → completed/failed
    run = AgentRun(
        user_id=current_user["user_id"],
        query=data.query,
        status="pending",
    )
    db.add(run)

    # ── Audit trail: log every query for security compliance ─────────
    db.add(AuditLog(
        user_id=current_user["user_id"],
        action="copilot_query",
        resource_type="agent_run",
        resource_id=run.id,
        details={"query": data.query},
    ))
    await db.flush()

    # ── Launch the pipeline as a background task ─────────────────────
    # FastAPI's BackgroundTasks runs this after the response is sent,
    # so the user doesn't wait for the full analysis to complete.
    # The frontend polls GET /copilot/runs/{run_id} for progress updates.
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
    """Get the status and results of a copilot analysis run.

    The frontend polls this endpoint to track pipeline progress. It returns:
        - Overall run status (pending/running/completed/failed)
        - Individual agent step statuses with execution times
        - Final results: root causes, recommendations, confidence score
        - The complete report content once generation is complete

    The response includes all AgentSteps sorted chronologically, allowing
    the frontend to render a real-time pipeline progress visualization.
    """
    # Eager-load the steps relationship to avoid N+1 queries
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")

    # Format agent steps for the response — sorted by creation time
    # so the frontend can display pipeline progress in order
    steps = [
        AgentStepResponse(
            agent_name=s.agent_name,
            status=s.status,
            execution_time_ms=s.execution_time_ms,
            # Truncate output to 200 chars for the summary view;
            # full output is available via the Report endpoint
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
