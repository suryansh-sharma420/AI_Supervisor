# Order Supervisor

An AI-powered order management system that runs autonomous agents to monitor and act on e-commerce orders. Each order gets a supervisor agent that watches for events (payment failures, shipment updates, delivery confirmations) and takes actions (messaging teams, creating notes, sleeping until the next check-in).

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- A [Groq](https://console.groq.com/) API key

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
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
DATABASE_URL=postgresql+asyncpg://localhost/order_supervisor
TEST_DATABASE_URL=postgresql+asyncpg://localhost/order_supervisor_test
GROQ_API_KEY=your_groq_api_key_here
ENVIRONMENT=development
```

Run migrations:

```bash
alembic upgrade head
```

Start the API server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
cd order_supervisor/frontend
npm install
```

Create a `.env.local` file in `frontend/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the dev server:

```bash
npm run dev
```

The UI is available at `http://localhost:3000`.

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
│   ├── tests/
│   │   ├── conftest.py        shared fixtures (engine, db session, dependency overrides)
│   │   └── phase1–6/
│   └── requirements.txt
└── frontend/
    ├── app/
    │   ├── layout.tsx         root layout with sidebar
    │   ├── page.tsx           redirects to /supervisors
    │   ├── supervisors/       supervisor list and CRUD
    │   └── runs/              runs list and run detail
    ├── components/
    │   ├── layout/            Sidebar, TopBar
    │   ├── ui/                Toast
    │   ├── supervisors/       SupervisorTable, SupervisorDrawer
    │   ├── runs/              RunStatCards, RunsTable, StartRunDrawer
    │   └── run-detail/        RunOverview, CurrentState, RuntimeInstructions,
    │                          ExecutiveControls, ActivityFeed, EventInjector, FinalSummary
    ├── hooks/                 useRun, useActivities
    ├── lib/                   api.ts, types.ts, utils.ts
    └── package.json
```

## Key Workflows

### Starting a Run

1. Create a supervisor configuration with a base instruction and list of available actions.
2. On the Runs page, click **+ Start Run**, select a supervisor, enter an order ID.
3. The run starts in `active` status. Click **Trigger Agent** to kick off the first agent cycle.

### Sending an Event

Events drive the system. POST to `/api/runs/{run_id}/events` with a type and optional data payload. The classifier decides whether the event should wake a sleeping run. Terminal events (`delivered`, `refund_requested`) automatically complete the run.

### Agent Cycle

When triggered, the agent reads current run state, builds a prompt with the supervisor's base instruction and recent events, and calls the Groq LLM with a set of tools. The agent calls tools (messaging teams, creating notes) until it calls `sleep()`, which schedules the next wake-up. The scheduler wakes sleeping runs automatically.

### Completion

Runs complete when:
- A terminal event arrives (`delivered`, `refund_requested`)
- An operator calls the terminate endpoint
- The run exceeds its `max_run_age_hours` limit (default 7 days)

On completion, a final summary is generated via LLM and stored on the run.
