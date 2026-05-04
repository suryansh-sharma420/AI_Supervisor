# API Reference

Base URL: `http://localhost:8000`

All request and response bodies are JSON. All timestamps are ISO 8601 in UTC.

---

## Health

### GET /health

Returns service health.

**Response 200**
```json
{ "status": "ok" }
```

---

## Supervisors

### POST /api/supervisors

Create a supervisor configuration.

**Request body**
```json
{
  "name": "Standard Order Supervisor",
  "base_instruction": "You are an order supervisor for an e-commerce platform...",
  "available_actions": ["message_fulfillment_team", "message_customer", "create_internal_note"],
  "wake_aggressiveness": "normal",
  "wake_up_behavior": null,
  "llm_settings": null
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| name | string | yes | |
| base_instruction | string | yes | Injected as system prompt in every agent cycle |
| available_actions | array of strings | no | Defaults to `[]`. Valid values listed under Tool Names below. |
| wake_aggressiveness | string | no | `"conservative"`, `"normal"`, or `"aggressive"`. Default `"normal"`. |
| wake_up_behavior | object | no | Reserved for future classifier rules |
| llm_settings | object | no | Reserved for future model overrides |

**Response 201**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Standard Order Supervisor",
  "base_instruction": "...",
  "available_actions": ["message_fulfillment_team", "message_customer", "create_internal_note"],
  "wake_aggressiveness": "normal",
  "wake_up_behavior": null,
  "llm_settings": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

### GET /api/supervisors

List all supervisors.

**Response 200** — array of supervisor objects (same shape as POST response).

---

### GET /api/supervisors/{supervisor_id}

Get a single supervisor.

**Response 200** — supervisor object.
**Response 404** — `{ "detail": "Supervisor not found" }`

---

### PATCH /api/supervisors/{supervisor_id}

Update a supervisor. All fields are optional; at least one must be provided.

**Request body** — any subset of supervisor fields.

**Response 200** — updated supervisor object.

---

### DELETE /api/supervisors/{supervisor_id}

Delete a supervisor.

**Response 204** — no body.
**Response 409** — `{ "detail": "Cannot delete supervisor with active runs" }`

---

## Runs

### POST /api/runs

Create a new run.

**Request body**
```json
{
  "supervisor_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "order_id": "ORD-12345",
  "max_run_age_hours": 168,
  "initial_state": {}
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| supervisor_id | UUID | yes | |
| order_id | string | yes | Your external order identifier |
| max_run_age_hours | integer | no | Default 168 (7 days) |
| initial_state | object | no | Merged into default state on creation |

**Response 201** — run object (see shape below).

---

### GET /api/runs

List all runs.

**Response 200** — array of run objects.

---

### GET /api/runs/{run_id}

Get a single run.

**Response 200**
```json
{
  "id": "uuid",
  "supervisor_id": "uuid",
  "order_id": "ORD-12345",
  "status": "sleeping",
  "state": {
    "order_status": "in_transit",
    "agent_summary": "Package shipped 2 days ago, estimated delivery tomorrow.",
    "custom_instructions": [],
    "events_since_last_wake": [],
    "iteration_count": 3,
    "last_action": "message_customer"
  },
  "wake_at": "2024-01-03T09:00:00Z",
  "started_at": "2024-01-01T10:00:00Z",
  "completed_at": null,
  "max_run_age_hours": 168,
  "final_summary": null,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Response 404** — `{ "detail": "Run not found" }`

---

### POST /api/runs/{run_id}/interrupt

Pause a run. Sets status to `paused`.

**Response 200** — `{ "message": "Run paused" }`

---

### POST /api/runs/{run_id}/resume

Resume a paused run. Sets status to `active`, clears `wake_at`.

**Response 200** — `{ "message": "Run resumed" }`

---

### POST /api/runs/{run_id}/terminate

Terminate a run immediately. Calls `complete_run()` — sets status to `terminated`, generates final summary.

**Response 200** — `{ "message": "Run terminated" }`

---

### POST /api/runs/{run_id}/instructions

Add a custom instruction to the run's state. Instructions are included in the agent's next context.

**Request body**
```json
{ "instruction": "Do not contact the customer until the package is 3 days overdue." }
```

**Response 200** — `{ "message": "Instruction added" }`

---

### GET /api/runs/{run_id}/activities

List all activities for a run, ordered by `created_at` ascending.

**Response 200** — array of activity objects:
```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "activity_type": "agent_action",
    "payload": {
      "tool": "message_fulfillment_team",
      "arguments": { "message": "Please expedite order ORD-12345." },
      "result": "Action recorded"
    },
    "created_at": "2024-01-01T10:05:00Z"
  }
]
```

---

## Events

### POST /api/runs/{run_id}/events

Ingest an event for a run. The classifier decides whether to wake a sleeping run.

**Request body**
```json
{
  "event_type": "payment_failed",
  "data": {
    "reason": "insufficient_funds",
    "amount": 149.99,
    "currency": "USD"
  }
}
```

**Event types:**

| Type | Category | Default classifier behavior |
|---|---|---|
| `payment_failed` | critical | always wake (hardcoded) |
| `delivered` | terminal | complete run (bypasses classifier) |
| `refund_requested` | terminal | complete run (bypasses classifier) |
| `shipment_created` | non-urgent | never wake (hardcoded) |
| `no_update_for_n_hours` | non-urgent | never wake (hardcoded) |
| `customer_message` | ambiguous | LLM classifier |
| `logistics_exception` | ambiguous | LLM classifier |
| `status_update` | ambiguous | LLM classifier |
| `custom` | ambiguous | LLM classifier |

**Response 200**
```json
{
  "event_type": "payment_failed",
  "data": { "reason": "insufficient_funds" },
  "run_id": "uuid",
  "wake_decision": true,
  "wake_reason": "Critical event: payment_failed always triggers wake",
  "activity_id": "uuid",
  "created_at": "2024-01-01T10:10:00Z"
}
```

---

## Trigger

### POST /api/runs/{run_id}/trigger

Manually trigger an agent cycle. The run must be in `active` status (not sleeping, running, paused, or terminal).

**Response 200** — `{ "message": "Agent cycle triggered" }`
**Response 400** — `{ "detail": "Run is not in a triggerable state" }`

---

## Wake

### POST /api/runs/{run_id}/wake

Manually wake a sleeping run. Sets status to `active`, clears `wake_at`, creates a `manual_wake` activity, then triggers an agent cycle.

Only works on runs with status `sleeping`.

**Response 200** — `{ "message": "Run woken and agent triggered" }`
**Response 400** — `{ "detail": "Run is not sleeping" }`

---

## Activity Types

| Type | When created |
|---|---|
| `run_created` | When a new run is created |
| `event_received` | When an event is ingested (one per event) |
| `wake_decision` | After classifier runs (records decision and reason) |
| `agent_action` | When the agent calls a business action tool |
| `state_update` | When the agent calls `update_state` |
| `sleep_decision` | When the agent calls `sleep` |
| `agent_error` | When the agent cycle encounters a Groq exception |
| `scheduled_wake` | When the scheduler wakes a sleeping run |
| `manual_wake` | When POST `/wake` is called |
| `system_event` | Generic system-level events |
| `final_output` | Created by `complete_run()` with completion reason and summary |

---

## Tool Names (for `available_actions`)

These are the valid values for a supervisor's `available_actions` list:

| Tool | Description |
|---|---|
| `message_fulfillment_team` | Send a message to the fulfillment team |
| `message_payments_team` | Send a message to the payments team |
| `message_logistics_team` | Send a message to the logistics team |
| `message_customer` | Send a message to the customer |
| `create_internal_note` | Create an internal note on the order |

`sleep` and `update_state` are always available to the agent regardless of `available_actions`.
