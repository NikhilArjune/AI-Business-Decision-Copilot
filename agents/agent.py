"""
AI Business Decision Copilot - ADK Agent Definitions
Root agent entry point using SequentialAgent + ParallelAgent orchestration.
"""

import os
import sys

# Add project root to path for tool imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from google.adk.agents import Agent, SequentialAgent, ParallelAgent

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
# =============================================================================

def create_data_agent():
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

# Phase 1: Data profiling (sequential - must run first)
# Phase 2: Parallel analysis (sales, inventory, marketing, support)
# Phase 3: Analytics + verification + recommendation + report (sequential)

root_agent = SequentialAgent(
    name="business_copilot",
    description="AI Business Decision Copilot - Multi-agent business analysis system",
    sub_agents=[
        # Step 1: Data profiling
        create_data_agent(),
        # Step 2: Parallel analysis of all business domains
        ParallelAgent(
            name="parallel_analysis",
            description="Run all domain-specific analyses concurrently",
            sub_agents=[
                create_sales_agent(),
                create_inventory_agent(),
                create_marketing_agent(),
                create_support_agent(),
            ],
        ),
        # Step 3: Analytics (anomaly detection + root cause)
        create_analytics_agent(),
        # Step 4: Verification
        create_verification_agent(),
        # Step 5: Recommendations
        create_recommendation_agent(),
        # Step 6: Final report
        create_report_agent(),
    ],
)
