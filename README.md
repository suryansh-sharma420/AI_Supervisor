# Order Supervisor — Autonomous Agent OSR

An AI-powered order management system that runs autonomous agents to monitor and act on e-commerce orders. Each order gets a dedicated supervisor agent that watches for events (payment failures, shipment updates, delivery confirmations) and takes intelligent actions (messaging teams, creating notes, or sleeping until the next check-in).

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **[Groq](https://console.groq.com/) API key** — uses `llama-3.3-70b-versatile` for the agent, `llama-3.1-8b-instant` for the classifier

---

## Quick Start

### 1. Database Setup

```bash
createdb order_supervisor
createdb order_supervisor_test
```

### 2. Backend Setup

```bash
cd order_supervisor/backend
python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
DATABASE_URL=postgresql+asyncpg://localhost/order_supervisor
TEST_DATABASE_URL=postgresql+asyncpg://localhost/order_supervisor_test
GROQ_API_KEY=your_groq_api_key_here
ENVIRONMENT=development
```

Run migrations and start the server:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Interactive API docs at `http://localhost:8000/docs`.

#### Clean Slate Reset

To wipe and recreate the database schema for a fresh demo environment:

```bash
python reset_db.py
```

### 3. Frontend Setup

```bash
cd order_supervisor/frontend
npm install
npm run dev
```

UI available at `http://localhost:3000`.

### 4. Running Tests

```bash
cd order_supervisor/backend
pytest tests/ -v
```

Tests are organized by phase:

```
tests/phase1/   schema and database tests
tests/phase2/   supervisor and run lifecycle tests
tests/phase3/   event ingestion and classifier tests
tests/phase4/   agent loop and tool calling tests
tests/phase5/   scheduler job tests
tests/phase6/   terminal events, summary, and completion tests
```

---

## Key Features

### Configurable Agent Pulse

Each supervisor has a `Default Sleep Duration` (minutes). When the agent finishes a cycle with no explicit sleep instruction, it falls back to this value — controlling how frequently the agent checks in on an order.

### Error Recovery

If an agent cycle hits a Groq error:
- The incoming event is **not lost** — it stays in `events_since_last_wake` for the next retry
- A 2-minute safety sleep is scheduled automatically
- A **Retry After Error** button appears in the UI for immediate manual recovery

### Dynamic Runtime Instructions

Operators can inject custom instructions into a running agent at any time from the run detail page. Instructions can also be **removed** individually, with every add and remove logged in the activity feed.

### Hybrid Event Classifier

Incoming events pass through a two-layer classifier:
- **Layer 1 (rules):** Critical events (`payment_failed`) always wake; non-urgent events (`shipment_created`) never wake
- **Layer 2 (LLM):** Ambiguous events are sent to `llama-3.1-8b-instant` with the supervisor's `wake_aggressiveness` setting influencing the decision
- Classifier failures default to `wake=True` so critical events are never silently dropped

---

## Project Structure

```
order_supervisor/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── design-decisions.md
│   └── api-reference.md
├── backend/
│   ├── alembic/               migration scripts
│   ├── reset_db.py            drops and recreates all tables
│   ├── app/
│   │   ├── main.py            FastAPI app, lifespan, router registration
│   │   ├── config.py          pydantic-settings config
│   │   ├── database.py        async SQLAlchemy engine and session
│   │   ├── dependencies.py    FastAPI dependency providers
│   │   ├── constants.py       terminal event set, valid statuses
│   │   ├── models/            SQLAlchemy ORM models
│   │   ├── schemas/           Pydantic request/response schemas
│   │   ├── routers/           FastAPI route handlers
│   │   ├── services/          business logic (run, supervisor, classifier, event, agent, summary)
│   │   ├── agent/             agent loop, tool definitions, context builder
│   │   └── scheduler/         APScheduler jobs and startup
│   └── tests/
│       ├── conftest.py        shared fixtures
│       └── phase1–6/
└── frontend/
    ├── app/
    │   ├── layout.tsx         root layout with sidebar
    │   ├── supervisors/       supervisor list and CRUD
    │   └── runs/              runs list and run detail
    ├── components/
    │   ├── layout/            Sidebar, TopBar
    │   ├── ui/                Toast
    │   ├── supervisors/       SupervisorTable, SupervisorDrawer
    │   ├── runs/              RunStatCards, RunsTable, StartRunDrawer
    │   └── run-detail/        RunOverview, CurrentState, RuntimeInstructions,
    │                          ExecutiveControls, ActivityFeed, EventInjector, FinalSummary
    ├── hooks/                 useRun (10s auto-refresh), useActivities
    └── lib/                   api.ts, types.ts, utils.ts
```

---

## Key Workflows

### Starting a Run

1. Create a supervisor on the Supervisors page — set a base instruction, choose available actions, and set a default sleep duration.
2. On the Runs page, click **+ Start Run**, select a supervisor, enter an order ID.
3. The run starts in `active` status. Click **Trigger Agent** to kick off the first agent cycle.

### Sending an Event

POST to `/api/runs/{run_id}/events` with a type and optional data, or use the **Event Injector** panel in the run detail UI. The classifier decides whether to wake a sleeping run. Terminal events (`delivered`, `refund_requested`) complete the run immediately.

### Agent Cycle

The agent reads current run state, builds a prompt from the supervisor's base instruction and recent events, then calls the Groq LLM with a set of tools. It calls business action tools until it calls `sleep()`, which schedules the next automatic wake-up. The scheduler polls every 60 seconds to wake sleeping runs whose `wake_at` has passed.

### Run Completion

Runs complete when:
- A terminal event arrives (`delivered`, `refund_requested`)
- An operator terminates the run from the UI
- The run exceeds its `max_run_age_hours` limit (default 7 days)

On completion, a final summary is generated by the LLM and displayed in the run detail panel.
