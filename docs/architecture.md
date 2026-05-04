# Architecture

## System Overview

Order Supervisor is a backend-heavy system where the interesting work happens in an asynchronous agent loop. The frontend is a thin operational dashboard — it reads state and sends commands, but all intelligence lives in the backend.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend                        │
│  Supervisors Page │ Runs List Page │ Run Detail Page            │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / REST
┌──────────────────────────────▼──────────────────────────────────┐
│                          FastAPI Backend                        │
│                                                                 │
│  /api/supervisors    /api/runs    /api/runs/{id}/events         │
│  /api/runs/{id}/trigger          /api/runs/{id}/wake            │
│                                                                 │
│  ┌─────────────────┐   ┌──────────────────────────────────┐     │
│  │  Event Service  │   │         Agent Service            │     │
│  │                 │   │                                  │     │
│  │  Classifier     │   │  Context Builder                 │     │
│  │  (rules → LLM)  │   │  Tool Definitions                │     │
│  │                 │   │  Agent Loop (Groq tool calling)  │     │
│  └────────┬────────┘   └───────────────┬──────────────────┘     │
│           │                            │                        │
│  ┌────────▼────────────────────────────▼──────────────────┐     │
│  │                    Run Service                         │     │
│  │  create_run  update_run_status  create_activity        │     │
│  └────────────────────────────┬───────────────────────────┘     │
│                               │                                 │
│  ┌────────────────────────────▼───────────────────────────┐     │
│  │                  Summary Service                       │     │
│  │  generate_final_summary   complete_run                 │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  APScheduler (in-process)                               │    │
│  │  wake_sleeping_runs — every 60s                         │    │
│  │  enforce_max_run_age — every 5 minutes                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
          ┌────────────────────┼──────────────────┐
          │                    │                  │
   ┌──────▼──────┐    ┌────────▼──────┐   ┌──────▼──────┐
   │ PostgreSQL  │    │  Groq API     │   │  APScheduler│
   │             │    │  (LLM calls)  │   │  (in-proc)  │
   │ supervisors │    │               │   └─────────────┘
   │ runs        │    │ classifier:   │
   │ activities  │    │  llama-3.1-8b │
   └─────────────┘    │ agent:        │
                      │  llama-3.3-70b│
                      └───────────────┘
```

## Database Schema

### supervisors

Stores reusable agent configurations. Each supervisor defines how its agents should behave.

| Column                  | Type        | Notes                                                                                       |
| ----------------------- | ----------- | ------------------------------------------------------------------------------------------- |
| id                      | UUID        | primary key                                                                                 |
| name                    | VARCHAR     | display name                                                                                |
| base_instruction        | TEXT        | system prompt injected into every agent cycle                                               |
| available_actions       | JSONB       | list of tool names the agent may call (e.g. `["message_customer", "create_internal_note"]`) |
| wake_up_behavior        | JSONB       | optional rules for the classifier (not yet active)                                          |
| wake_aggressiveness     | VARCHAR     | "conservative", "normal", or "aggressive" — influences classifier LLM prompt                |
| llm_settings            | JSONB       | optional overrides for model, temperature, etc.                                             |
| created_at / updated_at | TIMESTAMPTZ |                                                                                             |

### runs

One row per active order being supervised. Mutable state lives in the `state` JSONB column.

| Column                  | Type        | Notes                                                                                                                        |
| ----------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------- |
| id                      | UUID        | primary key                                                                                                                  |
| supervisor_id           | UUID FK     | which supervisor config to use                                                                                               |
| order_id                | VARCHAR     | external order identifier                                                                                                    |
| status                  | VARCHAR     | `active`, `sleeping`, `running`, `paused`, `completed`, `terminated`                                                         |
| state                   | JSONB       | current agent state (order_status, agent_summary, custom_instructions, events_since_last_wake, iteration_count, last_action) |
| wake_at                 | TIMESTAMPTZ | when a sleeping run should next wake; NULL otherwise                                                                         |
| started_at              | TIMESTAMPTZ |                                                                                                                              |
| completed_at            | TIMESTAMPTZ | set by `complete_run()`                                                                                                      |
| max_run_age_hours       | INTEGER     | default 168 (7 days); enforced by scheduler                                                                                  |
| final_summary           | TEXT        | generated at completion                                                                                                      |
| created_at / updated_at | TIMESTAMPTZ |                                                                                                                              |

### activities

Append-only log of everything that happens to a run. Drives the UI activity feed and provides the agent with its event history.

| Column        | Type        | Notes                                   |
| ------------- | ----------- | --------------------------------------- |
| id            | UUID        | primary key                             |
| run_id        | UUID FK     |                                         |
| activity_type | VARCHAR     | see Activity Types in the API reference |
| payload       | JSONB       | type-specific data                      |
| created_at    | TIMESTAMPTZ |                                         |

## Run Lifecycle

```
           ┌─────────┐
           │ created │  (POST /api/runs)
           └────┬────┘
                │
                ▼
           ┌─────────┐
           │ active  │ ◄──────────────────────────────┐
           └────┬────┘                                │
                │  trigger / wake                     │
                ▼                                     │
           ┌─────────┐                                │
           │ running │  (agent cycle executing)       │
           └────┬────┘                                │
                │                                     │
         ┌──────┴──────┐                              │
         │             │                              │
         ▼             ▼                              │
    ┌─────────┐   ┌──────────────┐                   │
    │sleeping │   │  completed   │                   │
    └────┬────┘   └──────────────┘                   │
         │                                           │
         │  wake_at reached (scheduler)              │
         │  or POST /wake                            │
         └───────────────────────────────────────────┘

Any non-terminal status → terminated (via operator or scheduler max age)
Any status → paused (interrupt) → active (resume)
```

**Status transitions:**

| From     | To         | Trigger                                              |
| -------- | ---------- | ---------------------------------------------------- |
| active   | running    | trigger or wake                                      |
| running  | sleeping   | agent calls `sleep()` tool                           |
| running  | completed  | terminal event or agent finishes with no sleep       |
| sleeping | active     | scheduler `wake_sleeping_runs` or POST `/wake`       |
| any      | paused     | POST `/interrupt`                                    |
| paused   | active     | POST `/resume`                                       |
| any      | terminated | POST `/terminate` or scheduler `enforce_max_run_age` |
| any      | completed  | terminal event (`delivered`, `refund_requested`)     |

## Agent Cycle

Each agent cycle is a single conversation with the Groq LLM using tool calling.

1. **Pre-check**: Reject if status is `terminated`, `completed`, or `running`.
2. **Status → running**: Set immediately to prevent concurrent execution.
3. **Increment iteration_count** in run state.
4. **Compact events**: If `events_since_last_wake` has more than 8 entries, summarize older ones into `agent_summary` and trim the list.
5. **Build prompts**: System prompt = supervisor's `base_instruction`. User prompt = current run state + recent events.
6. **LLM call with tools**: Uses `tool_choice="required"` on the first call to force an action. Subsequent calls use `"auto"`.
7. **Process tool calls**:
   - Business actions (message teams, create note) → logged as `agent_action` activity, continued.
   - `update_state` → updates `run.state[key]`, continued.
   - `sleep(duration_minutes, reason, next_check_focus)` → sets status `sleeping`, sets `wake_at`, clears `events_since_last_wake`, commits, **returns**.
8. **No tool call**: Default 60-minute sleep with a warning logged.
9. **Groq exception**: Log as `agent_error` activity, apply 30-minute emergency sleep.
10. **Max 10 iterations**: Safety limit per cycle to prevent runaway loops.

## Hybrid Classifier

The event classifier decides whether an incoming event should wake a sleeping run. It runs in two layers:

**Layer 1 — Hardcoded rules (free, instant):**

- `CRITICAL_EVENTS` (`payment_failed`, `delivered`, `refund_requested`) → always wake
- `NON_URGENT_EVENTS` (`no_update_for_n_hours`, `shipment_created`) → never wake
- Terminal events (`delivered`, `refund_requested`) → bypass classifier entirely, complete the run

**Layer 2 — LLM (only for ambiguous events):**

- Called when Layer 1 doesn't match
- Uses `llama-3.1-8b-instant` (fast, cheap)
- Prompt includes the supervisor's `wake_aggressiveness` setting
- Parse errors and API failures default to `wake=True` (fail-safe)

The classifier returns three values: `(should_wake: bool, reason: str, classifier_layer: str)`. The layer is recorded in the activity so operators can audit classifier behavior.

## Scheduler

Two APScheduler jobs run in-process alongside the FastAPI server:

**`wake_sleeping_runs` (every 60s):**
Queries for runs where `status = 'sleeping'` AND `wake_at <= now()`. For each, sets status to `active`, creates a `scheduled_wake` activity, then calls `execute_agent_cycle()`.

**`enforce_max_run_age` (every 5 minutes):**
Queries for non-terminal runs where `started_at + max_run_age_hours <= now()`. For each, calls `complete_run(reason="max_run_age_exceeded", final_status="terminated")`.

Both jobs create their own database sessions via `app.state.async_session_factory` (not FastAPI's `get_db()` dependency, which only works in request context).
