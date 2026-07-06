# 🎬 Video Script — AI Business Decision Copilot (Screen-Recording Walkthrough)

**How to use this:** You're just sharing your screen and talking. The lines in **plain text are what you read out loud.** The lines in `[SHOW: ...]` brackets tell you what to have on screen or click — you don't read those.

**Length:** ~4.5 minutes of talking. Speak at a normal, relaxed pace. It's fine to pause while the app works.

**Tip:** Do a practice run once. Keep the app already open and logged out, with sample data ready, before you hit record.

---

## PART 1 — Intro (about 25 seconds)

`[SHOW: the cover image OR the app login screen]`

> Hi, in this video I'll walk you through my capstone project — the **AI Business Decision Copilot**.
>
> It's a multi-agent AI system that reads a business's data — sales, inventory, marketing, and support — and answers questions like *"why did revenue drop this month?"* with a clear, evidence-backed diagnosis. Let me show you the problem it solves, and then a live demo of how it works.

---

## PART 2 — The Problem (about 30 seconds)

`[SHOW: open 2 or 3 of your sample CSV files quickly — sample_sales.csv, sample_inventory.csv, sample_marketing.csv]`

> Most businesses keep their data in separate files like these — sales in one, inventory in another, marketing and support in others. When revenue drops, someone has to open every file, look for patterns, and try to figure out the cause manually.
>
> That's slow, and it usually misses the real reason — because the real reason is often a *connection between* files. For example, a stockout in inventory causing a sales drop. My project automates all of that.

---

## PART 3 — Live Demo (about 90 seconds — the main part)

`[SHOW: log in to the app]`

> This is the app. It has a secure login with different user roles.

`[SHOW: the dashboard]`

> After logging in, you get a dashboard with key business metrics. But the real feature is the AI Copilot. Let me ask it a question.

`[SHOW: type into the copilot box: "Why did revenue decrease this month?" and press send]`

> I'll type: *"Why did revenue decrease this month?"* — and send it.

`[SHOW: the pipeline progress — agents going from running to completed]`

> Now you can see the agents working. First a Data agent checks the files, then four agents analyze sales, inventory, marketing, and support at the same time, and finally it verifies everything and writes the report. This takes a few seconds.

`[SHOW: the results — scroll slowly through the summary, root causes, and recommendations]`

> And here's the result. Instead of a vague answer, it gives a ranked list of root causes, each with a confidence score and the evidence behind it.
>
> The top cause here is an inventory stockout, at 92% confidence, backed by real numbers. Below that, a drop in marketing ROI, and a spike in customer complaints.

`[SHOW: point to the recommendations section]`

> And most importantly, it turns those causes into clear recommended actions — like which products to reorder and which campaign to pause. So it's not just a report; it tells you what to do next.

---

## PART 4 — How It Works / Architecture (about 45 seconds)

`[SHOW: open docs/images/architecture_diagram.png, or the README architecture section]`

> Let me quickly explain how it works behind the scenes. The system uses **11 specialized agents** built with Google's Agent Development Kit, in three phases.
>
> `[SHOW: point to Phase 1]` First, the Data agent validates the files.
>
> `[SHOW: point to Phase 2 — the four parallel agents]` Then four domain agents run **in parallel** — that's what makes it fast.
>
> `[SHOW: point to Phase 3]` Finally, an Analytics agent finds the anomalies and ranks the causes, a Verification agent checks that every claim is backed by data so nothing is made up, and Recommendation and Report agents create the final answer.

---

## PART 5 — The Code & Tech (about 40 seconds)

`[SHOW: open agents/agent.py briefly]`

> Here's the code. This file defines all the agents and how they're connected in sequence and in parallel.

`[SHOW: open mcp_server/server.py]`

> I also built an MCP server that exposes the business analysis tools using the Model Context Protocol.

`[SHOW: open backend/app/core/security.py, then docker-compose.yml]`

> On the backend I added real security — login tokens, user roles, and an audit log. And the whole thing runs with Docker Compose, so it's easy to deploy.
>
> So this project demonstrates four things from the course: a multi-agent system with ADK, an MCP server, security features, and deployability.

---

## PART 6 — Wrap Up (about 20 seconds)

`[SHOW: back to the app results screen or the cover image]`

> So that's the AI Business Decision Copilot. It takes something that used to take hours across many files, and answers it in seconds — with evidence you can trust and actions you can take.
>
> Thanks for watching!

---

## ✅ Quick recording checklist

- [ ] Use **OBS Studio** or **Loom** to record your screen at 1080p.
- [ ] Use a **headset mic**, not the laptop mic, in a quiet room.
- [ ] Have the app **already running** and sample data loaded before recording.
- [ ] Do the **demo query once before recording** to make sure it returns good results.
- [ ] If the pipeline is slow, you can **speed that part up** later in editing — or just stay quiet and let it run.
- [ ] Keep it **under 5 minutes**.
- [ ] Export as **MP4 (1080p)** and upload to YouTube as **Public or Unlisted**.
- [ ] Use `docs/images/cover.png` as the **thumbnail**.

---

## 🗣️ Full script — just the words to read (copy-paste)

> Hi, in this video I'll walk you through my capstone project — the AI Business Decision Copilot. It's a multi-agent AI system that reads a business's data — sales, inventory, marketing, and support — and answers questions like "why did revenue drop this month?" with a clear, evidence-backed diagnosis. Let me show you the problem it solves, and then a live demo of how it works.
>
> Most businesses keep their data in separate files like these — sales in one, inventory in another, marketing and support in others. When revenue drops, someone has to open every file, look for patterns, and figure out the cause manually. That's slow, and it usually misses the real reason — because the real reason is often a connection between files. For example, a stockout in inventory causing a sales drop. My project automates all of that.
>
> This is the app. It has a secure login with different user roles. After logging in, you get a dashboard with key business metrics. But the real feature is the AI Copilot. Let me ask it a question. I'll type: "Why did revenue decrease this month?" — and send it.
>
> Now you can see the agents working. First a Data agent checks the files, then four agents analyze sales, inventory, marketing, and support at the same time, and finally it verifies everything and writes the report. This takes a few seconds.
>
> And here's the result. Instead of a vague answer, it gives a ranked list of root causes, each with a confidence score and the evidence behind it. The top cause here is an inventory stockout, at 92% confidence, backed by real numbers. Below that, a drop in marketing ROI, and a spike in customer complaints. And most importantly, it turns those causes into clear recommended actions — like which products to reorder and which campaign to pause. So it's not just a report; it tells you what to do next.
>
> Let me quickly explain how it works behind the scenes. The system uses 11 specialized agents built with Google's Agent Development Kit, in three phases. First, the Data agent validates the files. Then four domain agents run in parallel — that's what makes it fast. Finally, an Analytics agent finds the anomalies and ranks the causes, a Verification agent checks that every claim is backed by data so nothing is made up, and Recommendation and Report agents create the final answer.
>
> Here's the code. This file defines all the agents and how they're connected in sequence and in parallel. I also built an MCP server that exposes the business analysis tools using the Model Context Protocol. On the backend I added real security — login tokens, user roles, and an audit log. And the whole thing runs with Docker Compose, so it's easy to deploy. So this project demonstrates four things from the course: a multi-agent system with ADK, an MCP server, security features, and deployability.
>
> So that's the AI Business Decision Copilot. It takes something that used to take hours across many files, and answers it in seconds — with evidence you can trust and actions you can take. Thanks for watching!
