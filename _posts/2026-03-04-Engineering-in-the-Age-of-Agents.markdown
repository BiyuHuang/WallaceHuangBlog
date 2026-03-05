---
title: "Engineering in the Age of Agents: Understanding Agent, Skill, and MCP"
date: 2026-03-04 20:00:00 +0800
description: A deep technical exploration of the Agent-Skill-MCP architecture — how these three components compose, where the boundaries lie, and what design patterns emerge in real-world engineering workflows.
image: /assets/img/agent_skill_mcp.png
tags: [AI, Agent, MCP]
categories: [Tech]
---

*Written by Biyu Huang, with [Cursor](https://www.cursor.com/) as co-author.*

---

## Beyond the Hype: A Systems Perspective

The AI discourse is dominated by model benchmarks and chatbot demos. But for engineers in the trenches, the real revolution is architectural: **how do you compose LLMs with tools, domain knowledge, and external systems to solve real problems?**

After months of building agent-powered workflows for data engineering — from requirement parsing to SQL generation to quality reporting — I've converged on a mental model with three distinct components: **Agent**, **Skill**, and **MCP**. Each has a clear role, and understanding their boundaries is the key to building systems that actually work.

---

## Agent: The Reasoning Loop

At its core, an Agent is an implementation of the **ReAct (Reasoning + Acting)** pattern:

```
while not goal_achieved:
    observation = perceive(environment)
    thought = reason(observation, goal, history)
    action = select_tool(thought)
    result = execute(action)
    history.append((thought, action, result))
```

This loop is deceptively simple but fundamentally different from traditional software. In a conventional pipeline, the control flow is static — you define every branch, every error handler, every retry. In an Agent loop, the control flow is **emergent**: the LLM decides what to do next based on what happened before.

### The Agent's Execution Model

Consider how an Agent handles a task like "generate a DWS table template from this Confluence requirement":

1. **Decomposition**: The Agent breaks the task into sub-goals — fetch the requirement, parse fields, validate table names, design architecture, generate SQL, optimize.
2. **Tool Selection**: For each sub-goal, the Agent selects the appropriate tool — an MCP connector for Confluence, a Skill for parsing, another Skill for SQL generation.
3. **Error Recovery**: When a table name validation fails, the Agent doesn't crash. It reasons about the failure, attempts correction (fuzzy matching, asking the user), and continues.
4. **State Management**: The Agent maintains a conversation history that serves as working memory, carrying context across tool calls.

This is fundamentally a **planner-executor** architecture, where the LLM is the planner and the tools are the executors. The quality of the system depends on three things: how well the planner reasons, how capable the executors are, and how cleanly they communicate.

### What Makes a Good Agent

From my experience, the difference between a useful Agent and a frustrating one comes down to:

- **Context window management**: Long workflows exhaust the context. Summarizing intermediate results and pruning history is critical.
- **Tool descriptions**: The Agent selects tools based on their descriptions. Vague descriptions lead to wrong tool selections. This is a UX problem disguised as an AI problem.
- **Structured output**: Agents that return free-form text are hard to compose. Forcing structured outputs (JSON, specific formats) at each step makes the pipeline reliable.
- **Human-in-the-loop checkpoints**: The most effective pattern isn't full autonomy — it's autonomy with confirmation gates at high-risk decision points.

---

## Skill: Codified Domain Expertise

A Skill is not a prompt. It's a **self-contained workflow specification** that encodes domain knowledge, constraints, and execution steps.

### Anatomy of a Skill

A well-designed Skill contains:

```yaml
# SKILL.md structure
name: create-sql-template
trigger: "User wants to generate new SparkSQL from requirements"

prerequisites:
  - Requirement markdown file exists in temp/requests/
  - Table names have been verified

workflow:
  1. Read the requirement spec
  2. Identify target table layer (DWD/DWS/ADS)
  3. Map source fields to target schema
  4. Generate SparkSQL with:
     - Correct partition strategy (dt-based incremental)
     - Proper null handling (nvl/coalesce)
     - Window functions for deduplication
     - get_json_object for nested fields
  5. Generate accompanying .conf file
  6. Output to template_todo/

constraints:
  - MUST use SparkSQL syntax (not Hive/Presto)
  - MUST follow team naming conventions (mart_dws_*, mart_dwd_*)
  - MUST include partition column in WHERE clause
  - MUST NOT use SELECT *
```

The critical insight: **Skills are the unit of reuse in agent systems.** They're analogous to functions in programming, but they operate at a higher level of abstraction — they encode *intent and methodology*, not just logic.

### Skill Design Patterns

Through building dozens of Skills, several patterns have emerged:

**1. Pipeline Skills**: Skills that chain together in a fixed sequence.

```
parse-request → architecture-design → create-sql-template → optimize-sql-template
```

Each Skill produces a structured artifact that the next Skill consumes. The Agent orchestrates the pipeline, but each step is a black box with clear inputs and outputs.

**2. Validation Skills**: Skills that verify rather than create.

```
verify-table-name  → Fuzzy matches against a knowledge base
verify-column      → Checks column existence via API with pagination
verify-logic       → Compares generated metrics against source docs
```

These are defensive Skills. They catch errors early and provide specific, actionable feedback rather than generic "something went wrong."

**3. Integration Skills**: Skills that bridge the gap between the Agent world and enterprise systems.

```
parse-request       → Reads from Confluence, outputs structured markdown
up-uat-quality-report → Runs validation queries, publishes to Confluence
```

These Skills are where most of the complexity lives — handling authentication, pagination, rate limiting, and format conversion.

### The Skill vs. Prompt Distinction

Why not just use a long prompt instead of a Skill? Three reasons:

1. **Composability**: Skills can be invoked by name. The Agent doesn't need to re-read 500 lines of instructions every time — it just calls `parse-request`.
2. **Versioning**: Skills can be updated independently. When your team's naming convention changes, you update one Skill, not every prompt that mentions table names.
3. **Testability**: A Skill has defined inputs and outputs. You can validate it against known test cases. A prompt is a black box.

---

## MCP: The Universal Tool Protocol

MCP (Model Context Protocol) solves a fundamental problem: **how does an Agent discover and interact with external tools without hardcoding every integration?**

### The Architecture

MCP follows a client-server model:

```
Agent (MCP Client)
    ↕ JSON-RPC over stdio/SSE
MCP Server (wraps external service)
    ↕ Native protocol
External Service (API, DB, file system...)
```

Each MCP server exposes three primitives:

- **Tools**: Actions the Agent can invoke (e.g., `confluence_get_page`, `jira_create_issue`)
- **Resources**: Read-only data the Agent can access (e.g., `confluence://page/12345`)
- **Prompts**: Pre-built prompt templates for common interactions

### Why MCP Matters Architecturally

Before MCP, every Agent framework had its own tool integration format. LangChain had its tools. AutoGPT had its plugins. Every integration was framework-specific.

MCP standardizes this. A Confluence MCP server works with Cursor, Claude Desktop, or any MCP-compatible client. This is the same pattern that made REST APIs universal — a shared protocol that decouples producers from consumers.

### Real-World MCP Topology

In my setup, multiple MCP servers compose into a rich environment:

```
Agent
├── MCP: Confluence    → Read requirements, publish reports
├── MCP: Jira          → Track tasks, update status
├── MCP: Google Sheets → Read/write tabular data
├── MCP: Data API      → Validate table names, fetch column metadata
├── MCP: SeaTalk       → Interactive feedback loop with users
└── MCP: Browser       → Navigate web UIs, take screenshots
```

Each MCP server is a separate process with its own lifecycle. The Agent discovers available tools at startup by reading the server's tool descriptors (JSON schema). This is **late binding** — the Agent doesn't know at compile time what tools are available; it discovers them at runtime.

### MCP Design Considerations

**Granularity**: Should you expose `search_confluence(query)` or `get_page(id)` + `search_pages(query)` + `get_page_content(id)`? Fine-grained tools give the Agent more flexibility but require more reasoning steps. Coarse-grained tools are faster but less composable. In practice, I find a **medium granularity** works best — one tool per logical operation, with clear input/output schemas.

**Error Handling**: MCP tools should return structured errors, not stack traces. The Agent needs to reason about what went wrong. `{"error": "page_not_found", "suggestion": "check page ID"}` is actionable. A 500-word Python traceback is not.

**Statelessness**: MCP tools should be stateless where possible. The Agent maintains state in its conversation history; tools should be pure functions of their inputs. This makes the system easier to debug and retry.

---

## The Composition: How It All Fits

Here's the full picture:

```
┌─────────────────────────────────────────────┐
│                   Agent                      │
│  ┌─────────────────────────────────────┐    │
│  │         Reasoning Loop (LLM)        │    │
│  │  observe → think → act → observe... │    │
│  └────────┬──────────────┬─────────────┘    │
│           │              │                   │
│     ┌─────▼─────┐  ┌────▼─────┐            │
│     │  Skills    │  │   MCP    │            │
│     │            │  │ Servers  │            │
│     │ • parse    │  │          │            │
│     │ • generate │  │ • Confl. │            │
│     │ • validate │  │ • Jira   │            │
│     │ • optimize │  │ • Data   │            │
│     └────────────┘  └──────────┘            │
└─────────────────────────────────────────────┘
```

**Agent** is the brain — it reasons and orchestrates.
**Skills** are the training — they provide domain methodology.
**MCP** is the hands — they connect to the physical world.

The power comes from composition. An Agent with one Skill and one MCP server is mildly useful. An Agent with 10 Skills and 6 MCP servers, each covering a different aspect of your workflow, becomes a force multiplier.

---

## Lessons from Production

### 1. Skills Are Your Competitive Moat

The LLM is a commodity. MCP servers are increasingly open-source. **Your Skills — the encoded expertise of how your team does things — are the irreplaceable piece.** Invest in writing, testing, and iterating on your Skills.

### 2. The 80/20 of MCP Integration

80% of the value comes from 3-4 MCP integrations that your team uses daily. Don't try to connect everything at once. Start with your team's information hub (Confluence/Notion), your task tracker (Jira/Linear), and your data catalog. Add more only when the Agent asks for it.

### 3. Debugging Agent Systems Is a New Discipline

Traditional debugging: read the stack trace, find the bug, fix it. Agent debugging: read the conversation history, understand *why* the Agent made that decision, figure out whether the problem is in the prompt, the Skill, the MCP tool, or the LLM's reasoning. We need better observability tools for this.

### 4. The Feedback Loop Is Everything

The most underrated pattern: **interactive feedback during execution**. Instead of fire-and-forget, the Agent pauses at critical points, presents its plan, and asks for confirmation. This turns a brittle autonomous system into a collaborative co-pilot. In my setup, the SeaTalk MCP server enables this — the Agent sends a summary and waits for my response before proceeding.

---

## Where This Architecture Is Heading

**Short-term (2026-2027):**
- Skills become shareable packages with standardized interfaces — think `npm install @team/sql-generation-skill`
- MCP becomes the universal standard. Every SaaS tool ships an MCP server alongside its REST API
- Multi-agent systems emerge, where specialized agents (data Agent, testing Agent, deployment Agent) collaborate via shared MCP channels

**Medium-term (2027-2029):**
- Agents maintain persistent memory across sessions, building up project context over weeks and months
- Skills become self-improving — the Agent refines Skills based on execution results and user feedback
- The line between "coding" and "operating agents" blurs. Senior engineers spend more time designing Skills and reviewing Agent output than writing code directly

**Long-term:**
- The engineering workflow inverts. Today we write code and occasionally use AI. Tomorrow we'll design intents and constraints, and agents will generate, test, and deploy the implementation. The engineer becomes the architect of the *process*, not the *product*.

---

## Closing Thoughts

The Agent-Skill-MCP architecture isn't just a technical pattern — it's a new way of thinking about software engineering. The Agent is the reasoning engine. Skills encode what you know. MCP connects to what you have. Together, they form a system that's greater than the sum of its parts.

The engineers who will thrive in this era aren't the ones who memorize API signatures or write the fastest code. They're the ones who can decompose complex workflows into clear Skills, design clean tool interfaces, and orchestrate agents to execute reliably.

The pipeline hasn't disappeared. It's just gotten a smarter operator.

---

*Interested in building agent-powered workflows? Check out the [MCP specification](https://modelcontextprotocol.io/) and start by building one Skill for your most repetitive task. You'll be surprised how fast things compound.*

*Find me on [GitHub](https://github.com/BiyuHuang).*
