import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app


async def _make_supervisor(client: AsyncClient, name: str = "Run Test Supervisor") -> str:
    resp = await client.post(
        "/api/supervisors",
        json={"name": name, "base_instruction": "Supervise runs."},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_run_happy_path() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client)
        resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-HAPPY"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["order_id"] == "ORD-HAPPY"
    assert data["status"] == "active"
    state = data["state"]
    assert state["order_id"] == "ORD-HAPPY"
    assert state["order_status"] == "created"
    assert state["iteration_count"] == 0
    assert state["custom_instructions"] == []
    assert state["events_since_last_wake"] == []
    assert state["last_action"] is None
    assert "agent_summary" in state


@pytest.mark.asyncio
async def test_create_run_supervisor_not_found() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/runs",
            json={"supervisor_id": str(uuid.uuid4()), "order_id": "ORD-NOSUP"},
        )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Supervisor not found"


@pytest.mark.asyncio
async def test_create_run_creates_run_started_activity() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Activity Check Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-ACT"},
        )
        run_id = run_resp.json()["id"]
        activities_resp = await client.get(f"/api/runs/{run_id}/activities")
    assert activities_resp.status_code == 200
    activities = activities_resp.json()
    assert len(activities) >= 1
    first = activities[0]
    assert first["activity_type"] == "system_event"
    assert first["payload"]["event"] == "run_started"
    assert first["payload"]["order_id"] == "ORD-ACT"


@pytest.mark.asyncio
async def test_list_runs_filter_by_status() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Filter Status Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-FILTER"},
        )
        run_id = run_resp.json()["id"]
        await client.post(f"/api/runs/{run_id}/terminate")

        active_resp = await client.get("/api/runs", params={"status": "active"})
        terminated_resp = await client.get("/api/runs", params={"status": "terminated"})

    active_ids = [r["id"] for r in active_resp.json()]
    terminated_ids = [r["id"] for r in terminated_resp.json()]
    assert run_id not in active_ids
    assert run_id in terminated_ids


@pytest.mark.asyncio
async def test_get_run_by_id() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Get Run Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-GETID"},
        )
        run_id = run_resp.json()["id"]
        resp = await client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.asyncio
async def test_add_instruction_appends_to_state() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Instruction Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-INSTR"},
        )
        run_id = run_resp.json()["id"]
        resp = await client.post(
            f"/api/runs/{run_id}/instructions",
            json={"instruction": "Escalate immediately"},
        )
    assert resp.status_code == 200
    assert "Escalate immediately" in resp.json()["state"]["custom_instructions"]


@pytest.mark.asyncio
async def test_add_instruction_creates_activity() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Instr Activity Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-INSTR-ACT"},
        )
        run_id = run_resp.json()["id"]
        await client.post(
            f"/api/runs/{run_id}/instructions",
            json={"instruction": "Do not refund"},
        )
        activities_resp = await client.get(f"/api/runs/{run_id}/activities")
    activities = activities_resp.json()
    manual = [a for a in activities if a["activity_type"] == "manual_instruction"]
    assert len(manual) == 1
    assert manual[0]["payload"]["instruction"] == "Do not refund"


@pytest.mark.asyncio
async def test_interrupt_run_becomes_paused() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Interrupt Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-INT"},
        )
        run_id = run_resp.json()["id"]
        resp = await client.post(f"/api/runs/{run_id}/interrupt")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_interrupt_run_already_paused_returns_409() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Double Interrupt Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-INT2"},
        )
        run_id = run_resp.json()["id"]
        await client.post(f"/api/runs/{run_id}/interrupt")
        resp = await client.post(f"/api/runs/{run_id}/interrupt")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Run is not in an interruptible state"


@pytest.mark.asyncio
async def test_resume_run_becomes_active() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Resume Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-RES"},
        )
        run_id = run_resp.json()["id"]
        await client.post(f"/api/runs/{run_id}/interrupt")
        resp = await client.post(f"/api/runs/{run_id}/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_resume_run_not_paused_returns_409() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Resume 409 Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-RES409"},
        )
        run_id = run_resp.json()["id"]
        resp = await client.post(f"/api/runs/{run_id}/resume")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Run is not paused"


@pytest.mark.asyncio
async def test_terminate_run_sets_status_and_completed_at() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Terminate Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-TERM"},
        )
        run_id = run_resp.json()["id"]
        resp = await client.post(f"/api/runs/{run_id}/terminate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "terminated"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_terminate_run_already_terminated_returns_409() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Double Terminate Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-TERM2"},
        )
        run_id = run_resp.json()["id"]
        await client.post(f"/api/runs/{run_id}/terminate")
        resp = await client.post(f"/api/runs/{run_id}/terminate")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Run is already finished"


@pytest.mark.asyncio
async def test_get_activities_ordered() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sup_id = await _make_supervisor(client, "Activities Order Supervisor")
        run_resp = await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-ACTORD"},
        )
        run_id = run_resp.json()["id"]
        await client.post(
            f"/api/runs/{run_id}/instructions",
            json={"instruction": "First instruction"},
        )
        await client.post(f"/api/runs/{run_id}/interrupt")
        resp = await client.get(f"/api/runs/{run_id}/activities")

    assert resp.status_code == 200
    activities = resp.json()
    assert len(activities) >= 3
    # Verify ordering: created_at is non-decreasing
    timestamps = [a["created_at"] for a in activities]
    assert timestamps == sorted(timestamps)
    types = [a["activity_type"] for a in activities]
    assert types[0] == "system_event"  # run_started
