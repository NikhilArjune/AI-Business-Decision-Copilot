# AI Business Decision Copilot

### A multi-agent system that reads your sales, inventory, marketing, and support data at once — and tells you *why* the numbers moved, with evidence.

**Track:** Agents for Business
**Built with:** Google Agent Development Kit (ADK) · MCP Server · Gemini 2.0 Flash · FastAPI · Docker

---

## The Problem

Every small and medium business is sitting on the answer to its most important question — *"why did this happen?"* — but the answer is scattered across half a dozen disconnected files. Sales live in one CSV export, inventory in a spreadsheet, marketing performance in a dashboard download, and customer complaints in a support-ticket log. Each system speaks a different format and none of them talk to each other.

So when revenue drops 18% in a month, the manager becomes a manual data analyst. They open five files, eyeball trends, try to remember what changed, and stitch together a story. This process is:

- **Slow** — hours or days pass before anyone acts, while the problem compounds.
- **Blind to cross-domain causes** — the real reason revenue fell is often that a *stockout* (inventory) killed sales of a top product that a *marketing campaign* was actively driving traffic to, while *support tickets* about delivery delays spiked. No single spreadsheet shows that chain. A human rarely connects all four.
- **Subjective** — without statistical backing, conclusions come down to gut feeling and whoever argues loudest in the meeting.
- **Repetitive** — the same tedious diagnostic ritual repeats for every new question.

Enterprise BI tools exist, but they're expensive, require data engineers to wire up, and still mostly *visualize* data rather than *reason* about it. There is no affordable, automated system that cross-analyzes all four business domains simultaneously and produces an evidence-backed diagnosis a busy owner can act on in seconds.

## Why Agents?

This problem is a near-perfect fit for a multi-agent system, and it's worth being precise about *why* — because the value isn't "we used AI," it's that the problem has a shape agents are uniquely good at.

The diagnostic workflow is **naturally decomposable**. "Why did revenue fall?" isn't one question — it's four specialist questions (What do sales show? Are we out of stock? Is marketing wasting money? Are customers unhappy?) followed by a synthesis step that only makes sense once you have all four answers. That is exactly a team of experts collaborating: each is a domain specialist, and a lead analyst combines their findings.

A single monolithic LLM prompt — "here's all my data, tell me what's wrong" — fails this problem in specific ways:

- It **misses cross-domain correlations** because everything is mashed into one context with no structured reasoning between domains.
- It has **no statistical rigor** — it can't run a Z-score anomaly detection inside a chat completion.
- It's **unverifiable** — it produces confident prose with no way to check whether each claim is backed by a real number.
- It **hits token limits** the moment datasets get large.

Agents solve all four: each specialist has a focused instruction and its own analysis tools, they run independently (and in parallel where possible), and a dedicated verification step gates out anything the data doesn't support. The multi-agent design isn't decoration — it *is* the solution.

## The Solution

**AI Business Decision Copilot** is a production-grade web application powered by a team of **11 specialized AI agents** orchestrated with Google's Agent Development Kit. The user experience is deliberately simple:

1. **Upload** business data (CSV/Excel) — sales, inventory, marketing, support tickets.
2. **Ask** a plain-English question: *"Why did revenue decrease this month?"*
3. **Watch** the agent pipeline analyze the data in parallel and in sequence, with live progress.
4. **Receive** a verified, evidence-backed report: ranked root causes with confidence scores, and prioritized, owner-assigned action items.

A real example of the output the pipeline produces:

```
📊 Executive Summary
Revenue decreased by 18.4% in June compared with May.

🔍 Root Causes (ranked by confidence):
  1. Stockout of top-selling products in Mobile Accessories
     Confidence: 92% | Impact: HIGH
     Evidence: 15 products below reorder level, inventory risk score 78%

  2. Marketing ROI dropped 32% after budget shifted to low-converting channels
     Confidence: 85% | Impact: HIGH
     Evidence: Campaign C has -12% ROI, $14,200 in wasted spend

  3. Customer complaints rose 41%, mainly delayed delivery
     Confidence: 78% | Impact: MEDIUM
     Evidence: Ticket volume up 41%, 63% negative sentiment

✅ Recommended Actions:
  1. [HIGH]   Reorder top 15 stockout SKUs immediately
  2. [HIGH]   Pause Campaign C, reallocate 40% budget to Campaign A
  3. [MEDIUM] Investigate delivery delays in the West region
```

Notice what makes this trustworthy: every root cause carries a **confidence score and the specific evidence** that produced it. This isn't an LLM guessing — it's a chain of statistical analysis that has been independently checked.

## Architecture

The system runs a **3-phase pipeline** that mirrors the natural dependency graph of business diagnosis, combining ADK's `SequentialAgent` and `ParallelAgent` primitives.

```
Phase 1 — Sequential:  Data Agent  (validate & profile every dataset first)
                            │
Phase 2 — Parallel:    Sales ║ Inventory ║ Marketing ║ Support
                            │   (independent domains → run concurrently, ~4× faster)
Phase 3 — Sequential:  Analytics → Verification → Recommendation → Report
                            (each step depends on the previous one's output)
```

**Phase 1 — Data Agent (Sequential).** Runs first and alone, because everything downstream depends on knowing the data is trustworthy. It reads each file, profiles schema and types, counts missing values and duplicates, and assigns a 0–100 quality score. If the data is corrupt, we catch it here instead of producing a confident diagnosis from garbage.

**Phase 2 — Four domain specialists (Parallel).** Sales, Inventory, Marketing, and Support agents run **concurrently** via `ParallelAgent`, because they operate on entirely independent datasets and never need each other's output. Each computes real metrics — the Sales agent does month-over-month revenue change and declining-product detection; Inventory flags stockouts and blocked stock; Marketing computes campaign ROI and wasted spend; Support does sentiment breakdown and spike detection. Running them in parallel gives roughly a **4× speedup** over sequential execution and makes the system fault-tolerant: one agent failing doesn't block the others.

**Phase 3 — Synthesis (Sequential).** This is where the cross-domain magic happens, and it must be ordered because each step consumes the last:

- **Analytics Agent** — the statistical brain. It runs Z-score anomaly detection on revenue, then fuses signals from all four domains into a **ranked root-cause list**, where each cause gets a confidence score scaled by how directly and strongly its domain drives revenue (a stockout caps higher than a soft sales dip).
- **Verification Agent** — the hallucination guard. It deliberately has **no tools**; it uses pure LLM reasoning to review every claim and reject anything not backed by specific data evidence. In a tool meant to inform money decisions, this quality gate is non-negotiable.
- **Recommendation Agent** — converts *verified* causes into 3–5 prioritized, actionable items with urgency, impact, and a suggested owner.
- **Report Agent** — compiles everything into an executive summary with Plotly charts.

Agents share results through ADK's `output_key` mechanism: each writes its findings to a named key in shared state, and downstream agents read upstream results without any manual data plumbing.

### The wider system

Around the agent pipeline sits a real product:

- A **FastAPI** backend (async, SQLAlchemy ORM) exposes a clean REST API. The `/copilot/query` endpoint kicks off the pipeline as a background task and returns immediately with a `run_id`; the frontend polls for live progress as each agent completes.
- A **static HTML/CSS/JS** SaaS dashboard — dark-themed, framework-free, instant-loading — handles login, data upload, and the analysis view.
- An **MCP Server** exposes the eight business-analysis tools over the open Model Context Protocol, so any MCP-compatible agent framework can reuse them.
- Everything is packaged as a **3-service Docker Compose** stack (backend, frontend, MCP server).

## Course Concepts Demonstrated

The capstone asks for at least three key concepts. This project meaningfully implements **four**:

1. **Multi-Agent System (ADK)** — 11 agents built with `google.adk.agents`, orchestrated through `SequentialAgent` + `ParallelAgent` with `output_key` state sharing. *(`agents/agent.py`)*
2. **MCP Server** — a FastMCP server exposing 8 reusable business tools (`analyze_sales`, `detect_anomalies`, `create_chart`, …) over the Model Context Protocol, independently Dockerized. *(`mcp_server/server.py`)*
3. **Security Features** — JWT authentication with bcrypt hashing, Role-Based Access Control across 4 roles (Admin/Manager/Analyst/Viewer), file-upload validation (type whitelist, 50 MB limit), and a full audit trail logging every user action. *(`backend/app/core/security.py`)*
4. **Deployability** — a 3-service Docker Compose deployment with health checks, volume mounts, and environment-based configuration. *(`docker-compose.yml`)*

## The Build & The Journey

I started from the **data**, not the agents. Before writing a single agent, I built a synthetic-data generator (`scripts/generate_data.py`) that produces realistic, *interconnected* business datasets — 10,000+ sales records where a genuine stockout in inventory actually causes a revenue dip in sales, and a marketing budget shift really does tank ROI. This mattered enormously: without correlated data, there would be no cross-domain story for the agents to discover, and the demo would be hollow.

The first hard design decision was **orchestration shape**. My initial instinct was a single powerful prompt. Testing killed that quickly — it produced fluent, plausible, and *unverifiable* answers that couldn't tie a claim to a number. That failure directly motivated the two most important architectural choices: splitting analysis into per-domain specialists so each computes real metrics, and adding a dedicated **Verification Agent** as a quality gate. Mapping the workflow's dependency graph onto ADK made the Sequential/Parallel split obvious — the four domains are independent, so they belong in a `ParallelAgent`; everything else is strictly ordered.

The second lesson was about **trust as a feature**. A business tool that's confidently wrong is worse than no tool. So confidence scores, explicit evidence strings, and the verification step aren't add-ons — they're the core value proposition. Every root cause the system emits can be traced back to a specific computed figure.

The third was **treating it as a product, not a notebook**. Real businesses need auth, roles, audit logs, and a deployable footprint. Building the FastAPI backend with JWT + RBAC, a static frontend that polls for live pipeline progress, and a Docker Compose stack turned a clever agent script into something a business could actually run — which is exactly what the "Agents for Business" track is about: impact where cost and revenue are on the line.

**Security hygiene** was a first-class concern throughout: secrets live only in a gitignored `.env` (with a committed `.env.example` template), there are zero API keys in the codebase, and all inputs pass Pydantic validation.

## Value & Impact

For a small business, this collapses a multi-hour, error-prone, cross-file investigation into a single natural-language question answered in seconds — with the statistical rigor and cross-domain reach a human analyst rarely achieves under time pressure. It doesn't just *show* charts; it *reasons* to a ranked, evidence-backed diagnosis and tells the owner exactly what to do next and in what order.

The architecture is also a **reusable pattern**: the specialist-agents-plus-verification design generalizes to any domain where you need to synthesize multiple independent data sources into a trustworthy, auditable conclusion — financial ops, healthcare triage, supply-chain risk. The business copilot is the demonstration; the pattern is the takeaway.

## Try It

The repository includes full setup instructions (local and Docker), sample datasets, and a suite of example questions. Get started in three commands:

```bash
git clone <repo-url> && cd ai-business-decision-copilot
cp .env.example .env      # add your GOOGLE_API_KEY
docker-compose up --build
```

Then open the dashboard, log in with the seeded demo account, and ask: *"Why did revenue decrease this month?"*

---

*Built for the 5-Day AI Agents: Intensive Vibe Coding Course with Google — Agents for Business track.*
