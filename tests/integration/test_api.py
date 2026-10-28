import pytest
from httpx import AsyncClient, ASGITransport

from src.adapters.api.app import app
from src.adapters.api.routes import get_repository
from tests.unit.test_use_cases import InMemoryTicketRepository


@pytest.fixture
def in_memory_repo():
    return InMemoryTicketRepository()


@pytest.fixture
def client(in_memory_repo):
    # Override FastAPI dependency to use in-memory repository for ultra-fast integration testing
    app.dependency_overrides[get_repository] = lambda: in_memory_repo
    transport = ASGITransport(app=app)
    client_instance = AsyncClient(transport=transport, base_url="http://test")
    yield client_instance
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_create_ticket_webhook_success(client: AsyncClient):
    payload = {
        "content": "My payment of $49 was deducted twice from my credit card yesterday! Please refund.",
        "channel": "web",
        "customer_email": "customer@company.com",
        "external_id": "CRM-HOOK-55",
    }
    response = await client.post("/api/v1/tickets/webhook", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["id"] is not None
    assert data["channel"] == "web"
    assert data["status"] == "new"
    assert data["external_id"] == "CRM-HOOK-55"

    classification = data["classification"]
    assert classification is not None
    assert classification["category"] == "billing"
    assert classification["urgency"] in ["high", "critical"]
    assert classification["confidence_score"] >= 0.85


@pytest.mark.asyncio
async def test_get_ticket_by_id_and_not_found(client: AsyncClient):
    # 1. Create a ticket
    create_resp = await client.post(
        "/api/v1/tickets/webhook",
        json={"content": "Server error 500 when accessing dashboard", "channel": "email"},
    )
    ticket_id = create_resp.json()["id"]

    # 2. Retrieve ticket by ID
    get_resp = await client.get(f"/api/v1/tickets/{ticket_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == ticket_id

    # 3. Retrieve non-existent ID
    fake_uuid = "018e0000-0000-7000-8000-000000000000"
    not_found_resp = await client.get(f"/api/v1/tickets/{fake_uuid}")
    assert not_found_resp.status_code == 404


@pytest.mark.asyncio
async def test_analytics_summary_endpoint(client: AsyncClient):
    # Ingest multiple diverse tickets
    tickets_to_ingest = [
        {"content": "Please refund my subscription fee immediately", "channel": "web"},
        {"content": "Error 500 exception stack trace in logs", "channel": "crm"},
        {"content": "Thank you for the wonderful product update!", "channel": "email"},
    ]
    for t in tickets_to_ingest:
        await client.post("/api/v1/tickets/webhook", json=t)

    # Query analytics
    analytics_resp = await client.get("/api/v1/analytics/summary")
    assert analytics_resp.status_code == 200
    summary = analytics_resp.json()

    assert summary["total_tickets"] == 3
    assert "billing" in summary["by_category"]
    assert "technical_issue" in summary["by_category"]
    assert summary["avg_confidence"] > 0.0
