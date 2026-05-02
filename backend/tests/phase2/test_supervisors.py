import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.run import Run


@pytest.mark.asyncio
async def test_create_supervisor_happy_path(db: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/supervisors",
            json={
                "name": "Test Supervisor",
                "base_instruction": "Monitor all orders.",
                "available_actions": ["message_customer"],
                "wake_aggressiveness": "normal",
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Supervisor"
    assert data["base_instruction"] == "Monitor all orders."
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_supervisor_missing_required_field() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/supervisors",
            json={"name": "No Instruction"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_supervisor_invalid_wake_aggressiveness() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/supervisors",
            json={
                "name": "Bad Supervisor",
                "base_instruction": "Do things.",
                "wake_aggressiveness": "extreme",
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_supervisors_empty() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Use a fresh db by checking with a unique name we won't create
        resp = await client.get("/api/supervisors")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_supervisors_returns_created() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/supervisors",
            json={"name": "List Test Sup", "base_instruction": "Watch it."},
        )
        resp = await client.get("/api/supervisors")
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert "List Test Sup" in names


@pytest.mark.asyncio
async def test_get_supervisor_by_id() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/supervisors",
            json={"name": "Get By ID", "base_instruction": "Fetch me."},
        )
        sup_id = create_resp.json()["id"]
        resp = await client.get(f"/api/supervisors/{sup_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sup_id


@pytest.mark.asyncio
async def test_get_supervisor_not_found() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/supervisors/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Supervisor not found"


@pytest.mark.asyncio
async def test_patch_supervisor_partial_update() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/supervisors",
            json={"name": "Patch Me", "base_instruction": "Original instruction."},
        )
        sup_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/supervisors/{sup_id}",
            json={"name": "Patched Name"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Patched Name"
    assert data["base_instruction"] == "Original instruction."


@pytest.mark.asyncio
async def test_delete_supervisor_no_active_runs(db: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/supervisors",
            json={"name": "Delete Me", "base_instruction": "Temporary."},
        )
        sup_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/supervisors/{sup_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_supervisor_with_active_runs(db: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/supervisors",
            json={"name": "Has Active Runs", "base_instruction": "Busy."},
        )
        sup_id = create_resp.json()["id"]
        await client.post(
            "/api/runs",
            json={"supervisor_id": sup_id, "order_id": "ORD-DEL-001"},
        )
        resp = await client.delete(f"/api/supervisors/{sup_id}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Cannot delete supervisor with active runs"
