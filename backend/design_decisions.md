# Order Supervisor: Core Design Decisions

This document serves as the architectural record for the Order Supervisor project, explaining the "Why" behind critical technical choices.

## Phase 1 & 2: Data & Connectivity
- **PostgreSQL JSONB**: We use JSONB for `state` and `payload` fields. This provides the flexibility of a NoSQL database (important for evolving agent state) with the ACID compliance and relational power of PostgreSQL.
- **NullPool Engine**: Implemented in `conftest.py` to resolve `InterfaceError` (another operation in progress). It ensures that every test gets a fresh, isolated connection, which is vital for async testing on Windows.
- **Manual Column Rename**: Renamed the database column `model_config` to `llm_settings` to resolve a conflict with Pydantic v2's reserved `model_config` attribute.
- **Lifespan Resources**: Moved Groq and DB cleanup to FastAPI's `lifespan` context manager to ensure resources are released even if the server crashes.

## Phase 3: The Intelligence Layer
- **Two-Tier Classification**: 
  1. **Rules Layer**: Fast, free, and local. It handles obvious critical events (e.g., `payment_failed`).
  2. **LLM Layer**: Intelligent classification via Groq/Llama3 for ambiguous scenarios. This balances cost and capability.
- **Briefing Accumulation**: Events are stored in `events_since_last_wake`. This allows the agent to wake up with "contextual memory" of everything that happened while it was offline.

## Phase 4: The Reasoning Loop
- **Vanilla Loop (No LangChain)**: We built the agent loop manually using raw Groq Tool Calling. This avoids library bloat, provides better stack traces, and gives us 100% control over the prompt/state synchronization.
- **Forced Tool Action**: We set `tool_choice: "required"` on the first turn. This forces the agent to take a physical action (like messaging a team or updating state) immediately upon waking up, preventing empty reasoning cycles.
- **Immediate Sleep Exit**: As soon as the agent calls the `sleep()` tool, the loop terminates. This prevents the model from attempting further tool calls after it has declared its task complete.
- **Tool Filtering**: Tools are dynamically generated based on the Supervisor's `available_actions` list. This acts as a "permission system" for the AI, preventing it from messaging unauthorized teams.
- **Loop Protection (Max 10)**: A hard cap on iterations prevents "Infinite Reasoning Loops" where the model might get stuck calling tools repeatedly, protecting against runaway API costs.

## Phase 5: Autonomous Scheduler & Lifecycle
- **AsyncIOScheduler (APScheduler)**: Implemented as a background singleton within the FastAPI lifespan. This allows for non-blocking "heartbeat" tasks that run alongside the API.
- **Isolated Session Factory**: Each background job creates its own database sessions via `app.state.async_session_factory`. This prevents a failure in one agent's reasoning cycle from affecting others (Failure Isolation).
- **PostgreSQL Native Intervals**: We use native SQL `interval` arithmetic for wake-time and run-age calculations. This shifts the heavy lifting to the database, ensuring the scheduler remains performant even with thousands of concurrent runs.
- **Status Re-verification**: Inside the scheduler loop, each run is re-fetched from the DB before being processed. This "double-check" pattern prevents race conditions between the autonomous scheduler and manual API triggers.

## Phase 6: Terminal States & Manual Overrides
- **Terminal Event Bypass**: Certain events (delivered, refund_requested) bypass the classification layer and trigger immediate completion. This ensures the system shuts down as soon as the business goal is reached.
- **Structured Final Output**: We enforced a 4-part reporting structure (Summary, Actions, Learnings, Recommendations) for the final LLM summary. This transforms the raw activity log into a human-readable professional report.
- **Decoupled Wake API**: We implemented a dedicated `/wake` endpoint separate from `/trigger`. This allows for explicit "Human-in-the-Loop" intervention to wake sleeping agents without waiting for the scheduler or an event.
## Phase 7: Full-Stack Frontend (Next.js)
- **Zero-Dependency UI**: All components (Toasts, Modals, Drawers) and icons (Inline SVGs) are custom-built with Tailwind CSS. This ensures a lightweight, high-performance bundle and maximum design flexibility.
- **Intelligent Polling (useActivities)**: Implemented a custom hook for the Activity Feed that manages its own heartbeat and cleanup. This provides a "Real-Time" feel to the dashboard without the complexity of WebSockets.
- **Promise-Based Routing**: Leveraged Next.js 14's `use(params)` pattern to unwrap dynamic route parameters, ensuring compatibility with the latest React Server Component standards.
- **Executive Control Suite**: Each action button (Trigger, Terminate, Resume) is an independent "smart" component with its own loading state and inline confirmation logic, preventing the UI from locking up during long AI reasoning cycles.
