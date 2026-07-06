"""
AI Business Decision Copilot - ADK Agent Definitions
Root agent entry point using SequentialAgent + ParallelAgent orchestration.

ARCHITECTURE OVERVIEW:
    This module defines the multi-agent system using Google's Agent Development Kit (ADK).
    The system uses 11 specialized agents organized in a 3-phase pipeline:

    Phase 1 (Sequential): Data Agent validates and profiles uploaded datasets.
                           This MUST run first because all subsequent agents depend on
                           knowing the data schema, quality, and available columns.

    Phase 2 (Parallel):    Four domain-specific agents (Sales, Inventory, Marketing, Support)
                           run CONCURRENTLY via ParallelAgent. These agents analyze independent
                           datasets and don't depend on each other's output, making parallel
                           execution safe and ~4x faster than sequential.

    Phase 3 (Sequential):  Analytics → Verification → Recommendation → Report agents run
                           in strict sequence because each depends on the previous agent's
                           output. The Analytics Agent needs all domain findings to detect
                           cross-domain patterns. The Verification Agent needs analytics
                           results to validate. And so on.

DESIGN DECISIONS:
    - Each agent uses `output_key` to store its results in ADK's shared state.
      This allows downstream agents to access upstream results without explicit
      data passing. For example, the Verification Agent can read `sales_findings`,
      `inventory_findings`, etc. from the shared conversation state.

    - All agents use gemini-2.0-flash for fast inference. This model provides
      good reasoning capability while keeping latency under 2 seconds per agent.

    - The Verification Agent has NO tools — it uses pure LLM reasoning to validate
      claims made by other agents. This is intentional: verification should be
      independent of the same tools that generated the findings.

    - The Recommendation Agent also has NO tools — it synthesizes verified findings
      into actionable business decisions using the LLM's reasoning capabilities.

AGENT FLOW:
    User Query → Data Agent → [Sales | Inventory | Marketing | Support] → Analytics
    → Verification → Recommendation → Report → Final Answer
"""

import os
import sys

# Add project root to path so tool modules can be imported from agents/tools/
# This is necessary because ADK loads this file as the agent entry point,
# and the tools live in sibling directories relative to the agents package.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from google.adk.agents import Agent, SequentialAgent, ParallelAgent

# Import all tool functions that agents will use.
# Each tool is a plain Python function decorated for ADK compatibility.
# Tools are grouped by business domain for maintainability.
from agents.tools.data_tools import read_uploaded_file, profile_dataset_tool
from agents.tools.sales_tools import run_sales_analysis
from agents.tools.inventory_tools import run_inventory_analysis
from agents.tools.marketing_tools import run_marketing_analysis
from agents.tools.support_tools import run_support_analysis
from agents.tools.analytics_tools import run_anomaly_detection, run_root_cause_ranking
from agents.tools.chart_tools import generate_chart
from agents.tools.report_tools import generate_report


# =============================================================================
# Specialist Agents
# Each agent is created via a factory function to ensure fresh instances
# when building the agent tree. ADK requires unique agent instances in
# the sub_agents list (no shared references).
# =============================================================================

def create_data_agent():
    """Create the Data Agent — the first agent in the pipeline.

    Purpose: Validates uploaded business data files before any analysis begins.
    This prevents downstream agents from working with corrupt, incomplete,
    or incorrectly formatted data.

    Behavior:
        1. Reads CSV/Excel files using the read_uploaded_file tool
        2. Profiles data quality using profile_dataset_tool
        3. Reports schema (column names, types), missing values, duplicates
        4. Assigns a quality score (0-100) to guide confidence in later analysis

    Output Key: 'data_profile' — stored in ADK shared state for all other agents
    """
    return Agent(
        name="data_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Data Agent. Your job is to validate and profile business datasets.

        When given a file path:
        1. Read the file using read_uploaded_file
        2. Profile it using profile_dataset_tool
        3. Report the data quality, schema, and any issues

        Store your findings in a structured format for other agents to use.
        Focus on: column types, missing values, duplicates, data quality score.""",
        description="Validates and profiles business datasets for quality and schema.",
        tools=[read_uploaded_file, profile_dataset_tool],
        output_key="data_profile",
    )


def create_sales_agent():
    """Create the Sales Agent — analyzes revenue and sales performance.

    Purpose: Computes key revenue metrics that form the foundation of most
    business diagnostics. Revenue trends are often the starting point for
    understanding "why did things change?"

    Business Logic:
        - Month-over-month revenue comparison to detect growth or decline
        - Product-level performance ranking to find winners and losers
        - Regional breakdown to identify geographic patterns
        - Declining product detection (>10% drop threshold) for early warnings

    Output Key: 'sales_findings' — used by Analytics Agent for root cause ranking
    """
    return Agent(
        name="sales_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Sales Agent. Analyze revenue and sales performance.

        Use run_sales_analysis to compute:
        - Monthly revenue trends
        - Revenue change percentage (month-over-month)
        - Top and bottom performing products
        - Category and regional performance
        - Declining products

        Provide clear findings with specific numbers. Flag any significant declines (>10%).""",
        description="Analyzes revenue trends, product performance, and sales patterns.",
        tools=[run_sales_analysis],
        output_key="sales_findings",
    )


def create_inventory_agent():
    """Create the Inventory Agent — detects supply chain issues.

    Purpose: Identifies inventory-related problems that directly impact revenue.
    Stockouts are one of the most common (and preventable) causes of revenue drops.

    Business Logic:
        - Stockout detection: products with zero or below-reorder-level stock
        - Low stock alerts: products approaching reorder threshold
        - Blocked inventory: stock that exists but can't be sold (damaged, held, etc.)
        - Cross-referencing with sales data to check if stockouts correlate with
          declining product sales — a key causal signal

    Output Key: 'inventory_findings' — used by Analytics Agent for root cause ranking
    """
    return Agent(
        name="inventory_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Inventory Agent. Detect inventory-related business issues.

        Use run_inventory_analysis to identify:
        - Stockout products (zero or below reorder level)
        - Low stock alerts
        - Blocked inventory
        - Inventory risk score by category

        Cross-reference with sales data in the state to identify if stockouts match declining products.""",
        description="Detects stockouts, low stock, blocked inventory, and supply-demand gaps.",
        tools=[run_inventory_analysis],
        output_key="inventory_findings",
    )


def create_marketing_agent():
    """Create the Marketing Agent — evaluates campaign effectiveness.

    Purpose: Determines if marketing spend is generating adequate returns.
    Poor marketing ROI is a common but often overlooked cause of revenue decline,
    because the money is spent but doesn't translate to sales.

    Business Logic:
        - Campaign-level ROI calculation: (revenue - spend) / spend × 100
        - Cost per acquisition (CPA): spend / conversions
        - Channel comparison: which channels deliver best ROI
        - Wasted spend detection: sum of spend on campaigns with negative ROI
        - ROI trend analysis: is marketing getting more or less efficient?

    Output Key: 'marketing_findings' — used by Analytics Agent for root cause ranking
    """
    return Agent(
        name="marketing_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Marketing Agent. Evaluate marketing campaign effectiveness.

        Use run_marketing_analysis to compute:
        - Campaign ROI and ROI trends
        - Cost per acquisition
        - Channel performance comparison
        - Underperforming and best-performing campaigns
        - Wasted marketing spend

        Flag any campaigns with negative ROI or significant ROI decline.""",
        description="Evaluates campaign ROI, channel performance, and marketing spend efficiency.",
        tools=[run_marketing_analysis],
        output_key="marketing_findings",
    )


def create_support_agent():
    """Create the Support Agent — analyzes customer complaints and sentiment.

    Purpose: Customer complaints are a lagging indicator of business problems.
    A spike in complaints about delivery delays, for example, often correlates
    with fulfillment issues that also impact repeat purchase rates.

    Business Logic:
        - Complaint categorization: groups tickets by issue type
        - Sentiment analysis: positive/neutral/negative breakdown
        - Spike detection: flags >20% increase in ticket volume (indicates emerging issues)
        - Product-level complaint ranking: which products generate the most complaints
        - Resolution time analysis: how quickly issues are being addressed

    Output Key: 'support_findings' — used by Analytics Agent for root cause ranking
    """
    return Agent(
        name="support_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Customer Support Agent. Analyze customer complaints and sentiment.

        Use run_support_analysis to identify:
        - Complaint category distribution
        - Sentiment breakdown (positive/neutral/negative)
        - Ticket volume trends and spikes
        - Top-complained products
        - Average resolution time

        Flag complaint spikes (>20% increase) and high negative sentiment.""",
        description="Analyzes customer complaints, sentiment trends, and support ticket patterns.",
        tools=[run_support_analysis],
        output_key="support_findings",
    )


def create_analytics_agent():
    """Create the Analytics Agent — performs cross-domain anomaly detection.

    Purpose: This is the synthesis agent. It takes findings from all four domain
    agents (sales, inventory, marketing, support) and looks for CROSS-DOMAIN
    patterns that individual agents can't see. For example:
        - Stockouts in inventory + declining product sales → supply-caused revenue loss
        - Marketing ROI drop + ticket spike → bad campaign driving complaints

    Business Logic:
        - Z-score based anomaly detection on daily/monthly revenue
        - Category-level decline detection (>15% drop)
        - Root cause ranking: combines signals from all agents into a confidence-scored
          list of probable causes, ordered by likelihood

    Output Key: 'analytics_findings' — the ranked root causes that drive recommendations
    """
    return Agent(
        name="analytics_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Analytics Agent. Perform anomaly detection and root cause analysis.

        Use run_anomaly_detection on sales data to find:
        - Daily revenue anomalies (Z-score based)
        - Monthly revenue drops
        - Category-level declines

        Then synthesize findings from all other agents (available in the conversation)
        to produce a ranked list of root causes with confidence scores.

        Each root cause should have: cause description, category, confidence (0-1), impact level, evidence, and recommended action.""",
        description="Performs statistical anomaly detection and ranks root causes by confidence.",
        tools=[run_anomaly_detection],
        output_key="analytics_findings",
    )


def create_verification_agent():
    """Create the Verification Agent — the hallucination guard.

    Purpose: LLMs can generate plausible-sounding business insights that aren't
    actually supported by the data. This agent acts as a quality gate that
    prevents unverified claims from reaching the final report.

    Design Choice: This agent has NO tools intentionally. It uses pure LLM
    reasoning to review other agents' outputs and check if every claim has
    supporting data evidence. Using the same analysis tools would create
    circular validation — we want independent reasoning.

    Behavior:
        1. Reviews each finding from other agents
        2. Checks if specific data evidence supports each claim
        3. Rejects or flags conclusions without evidence
        4. Validates that calculations and percentages are mathematically reasonable
        5. Assigns confidence scores (0-1) based on evidence strength

    Output Key: 'verified_findings' — only evidence-backed claims pass through
    """
    return Agent(
        name="verification_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Verification Agent. Your role is to prevent hallucinated business claims.

        Review the findings from other agents and:
        1. Check if every claim is supported by specific data evidence
        2. Reject or flag any conclusions without evidence
        3. Validate that calculations and percentages are reasonable
        4. Assign a confidence score (0-1) to each finding
        5. Note any data limitations that could affect conclusions

        Output a verified set of findings with evidence citations.""",
        description="Validates every business claim has supporting data evidence.",
        output_key="verified_findings",
    )


def create_recommendation_agent():
    """Create the Recommendation Agent — converts analysis into action items.

    Purpose: Business owners don't want raw data analysis — they want to know
    "what should I do?" This agent translates verified root causes into
    specific, prioritized, actionable recommendations.

    Design Choice: No tools, pure LLM reasoning. The recommendations are
    generated from the verified findings, not from raw data. This ensures
    every recommendation traces back to evidence-backed analysis.

    Behavior:
        - Generates 3-5 prioritized action items (not vague, highly specific)
        - Each action includes: urgency level, estimated impact, suggested owner
        - Ordered by business impact (highest first)
        - Includes timeline suggestions for implementation

    Output Key: 'recommendations' — the actionable output for business owners
    """
    return Agent(
        name="recommendation_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Recommendation Agent. Generate actionable business decisions.

        Based on the verified root causes and analysis findings:
        1. Generate 3-5 prioritized action items
        2. For each action: specify urgency (high/medium/low), estimated impact, and suggested owner
        3. Order by business impact
        4. Be specific and actionable (not vague)
        5. Include timeline suggestions

        Format each recommendation with: priority number, action, urgency, impact, owner, timeline.""",
        description="Converts analysis into prioritized, actionable business recommendations.",
        output_key="recommendations",
    )


def create_report_agent():
    """Create the Report Agent — produces the final executive deliverable.

    Purpose: Compiles all findings, root causes, and recommendations into
    a structured executive report suitable for CEO-level presentation.

    Tools:
        - generate_chart: Creates Plotly visualizations (line, bar, pie charts)
        - generate_report: Formats the final report with sections and evidence

    Output Key: 'final_report' — the complete executive report
    """
    return Agent(
        name="report_agent",
        model="gemini-2.0-flash",
        instruction="""You are the Report Agent. Create the final executive business report.

        Compile all findings into a structured report:
        1. Executive Summary (2-3 sentences)
        2. Key Metrics (revenue change, order volume, etc.)
        3. Root Cause Analysis (ranked list with evidence)
        4. Recommended Actions (prioritized)
        5. Data Sources and Confidence Score

        Use clear, professional language suitable for a CEO or board meeting.
        Include specific numbers and percentages. Avoid jargon.""",
        description="Creates the final executive business report with all findings.",
        tools=[generate_chart, generate_report],
        output_key="final_report",
    )


# =============================================================================
# Orchestration: SequentialAgent + ParallelAgent
# =============================================================================
#
# WHY THIS DESIGN:
# The business analysis workflow has a natural dependency graph:
#
#   Data Agent (MUST run first — validates data)
#       ↓
#   Sales ║ Inventory ║ Marketing ║ Support  (INDEPENDENT — safe to parallelize)
#       ↓
#   Analytics Agent (NEEDS all domain findings to detect cross-domain patterns)
#       ↓
#   Verification Agent (NEEDS analytics output to validate)
#       ↓
#   Recommendation Agent (NEEDS verified findings to generate actions)
#       ↓
#   Report Agent (NEEDS everything above to compile final report)
#
# SequentialAgent ensures each phase completes before the next starts.
# ParallelAgent in Phase 2 gives us ~4x speedup since the four domain
# agents operate on independent datasets and don't share state.
#
# ADK's output_key mechanism handles data flow between agents:
# Each agent writes its output to a named key in the shared state,
# and downstream agents can read any upstream agent's output.
# =============================================================================

root_agent = SequentialAgent(
    name="business_copilot",
    description="AI Business Decision Copilot - Multi-agent business analysis system",
    sub_agents=[
        # ── Phase 1: Data Validation (Sequential) ──────────────────────────
        # Must run first to validate data quality before analysis begins.
        # If data is corrupt or missing critical columns, we catch it early.
        create_data_agent(),

        # ── Phase 2: Domain Analysis (Parallel) ───────────────────────────
        # Four specialist agents run CONCURRENTLY because they analyze
        # independent datasets (sales.csv, inventory.csv, marketing.csv,
        # support_tickets.csv). No data dependencies between them.
        # ParallelAgent provides ~4x speedup over sequential execution.
        ParallelAgent(
            name="parallel_analysis",
            description="Run all domain-specific analyses concurrently",
            sub_agents=[
                create_sales_agent(),       # Analyzes: sample_sales.csv
                create_inventory_agent(),   # Analyzes: sample_inventory.csv
                create_marketing_agent(),   # Analyzes: sample_marketing.csv
                create_support_agent(),     # Analyzes: sample_support_tickets.csv
            ],
        ),

        # ── Phase 3: Synthesis & Output (Sequential) ──────────────────────
        # These agents run in strict order because each depends on the
        # previous agent's output for correctness.
        create_analytics_agent(),       # Combines all domain findings → root causes
        create_verification_agent(),    # Validates claims have evidence backing
        create_recommendation_agent(),  # Converts verified causes → action items
        create_report_agent(),          # Compiles everything → executive report
    ],
)
