# Design Decisions

## 1. APScheduler Over a Dedicated Worker Queue

**Decision:** Background jobs (waking sleeping runs, enforcing max age) run as APScheduler jobs inside the FastAPI process, not as Celery workers, separate processes, or a managed workflow engine like Temporal.

**Rationale:** The jobs are simple cron-style scans — query some rows, kick off agent cycles. They don't need distributed execution, retry queues, or inter-worker communication. Running them in-process eliminates infrastructure: no Redis, no Celery worker deployment, no separate process to monitor. The tradeoff is that if the API server goes down, no jobs run. For a single-server deployment this is fine. If the system needed multi-instance scale-out or crash recovery, a proper task queue would be warranted.

---

## 2. JSONB for Run State

**Decision:** The agent's working state (order_status, agent_summary, custom_instructions, iteration_count, etc.) is stored in a single JSONB column on the `runs` table rather than as typed columns.

**Rationale:** Agent state is schema-unstable. Different supervisors need different state keys; state keys get added and removed as the agent reasons. Forcing a rigid column schema would require a migration every time an agent prompt evolves. JSONB gives the agent a free-form scratchpad while keeping the data in the database (visible, queryable, backed up). The core status tracking (run status, timestamps, supervisor linkage) uses typed columns because those fields are always present and queried directly.

---

## 3. Single Activities Table as Audit Log

**Decision:** All events — agent actions, sleep decisions, wake events, classifier decisions, system errors, final output — are stored as rows in a single `activities` table with a `type` discriminator and JSONB `payload`, rather than separate tables per event type.

**Rationale:** The activity feed is the primary debugging and auditing tool. A single table means a single query for "show me everything that happened to this run in order." Type-specific tables would require unions or separate queries to reconstruct the timeline. The downside is that the payload schema is not enforced by the database, but each activity type has a well-defined payload shape in the application layer, and the flexibility is worth the tradeoff for a system where new activity types are added often.

---

## 4. Two-Layer Hybrid Classifier

**Decision:** Event classification uses hardcoded rules first, falling back to an LLM only for events that rules don't match — rather than sending every event to the LLM.

**Rationale:** Most events are obviously critical (`payment_failed`) or obviously ignorable (`no_update_for_n_hours`). Sending those to an LLM adds latency and cost for no benefit. The LLM adds value only for ambiguous events like `customer_message` or `logistics_exception`, where context and the supervisor's aggressiveness setting should influence the decision. The fail-safe default (LLM errors → wake=True) means the system errs on the side of over-waking rather than missing critical events. This is the right bias for an order management system.

---

## 5. Sequential Tool Execution Within One Agent Cycle

**Decision:** The agent calls tools one at a time in a single-threaded loop rather than invoking multiple tools in parallel.

**Rationale:** Order management actions have dependencies. You want to message the fulfillment team *before* messaging the customer, create an internal note *after* deciding on an action. Parallel execution would make ordering non-deterministic and harder to audit. The activities log is also cleaner — each agent action is recorded in sequence, making the feed readable as a narrative. Latency from sequential tool calls is not a concern because the "tools" are mostly just database writes; the real latency is the LLM calls, which are sequential by nature.

---

## 6. System-Owned Completion via `complete_run()`

**Decision:** All three completion paths (terminal events, manual terminate, scheduler max age) call a single `complete_run()` function rather than each path implementing its own completion logic.

**Rationale:** Before this consolidation, the three paths each did slightly different things: different activity types, inconsistent handling of `completed_at`, no summary generation in some paths. `complete_run(reason, final_status)` ensures every completed or terminated run has a `completed_at` timestamp, a `final_summary`, and a `final_output` activity in the log. One function to audit, one function to test, one place to add new completion behavior.

---

## 7. Event Compaction at 8-Event Threshold

**Decision:** When `events_since_last_wake` grows beyond 8 entries, older events are summarized into `agent_summary` and the list is trimmed to the 8 most recent entries before the LLM call.

**Rationale:** Long-running orders can accumulate dozens of events between agent cycles (e.g., a package that spends two weeks in transit). Without compaction, the context window fills up and eventually the LLM call fails or the most recent events get truncated. The threshold of 8 is a pragmatic choice — recent enough to give the agent full detail on what just happened, while offloading the history into a compact summary. The summary is generated by the application (not the LLM) for cost reasons; it's a simple concatenation of the older event descriptions.

---

## 8. No Authentication

**Decision:** The API has no authentication layer.

**Rationale:** This is an internal operational tool deployed inside a private network. Adding auth (JWT, API keys, OAuth) would add significant complexity — token management, user tables, middleware — for no security benefit in the current deployment context. If the system were exposed externally or multi-tenant, auth would be the first thing to add. The explicit non-decision is documented here so future developers know it was intentional, not an oversight.
