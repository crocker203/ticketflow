import pytest
from src.adapters.db.session import async_session_maker
from src.adapters.db.repository import PostgresTicketRepository
from src.adapters.classifier.classifier import SmartRuleBasedClassifier
from src.services.ingest_ticket import IngestTicketUseCase
from src.services.analytics import GetAnalyticsUseCase
from src.domain.enums import TicketChannel, TicketStatus


@pytest.mark.asyncio
async def test_live_postgres_flow():
    """End-to-end integration test executing real queries against PostgreSQL 16."""
    async with async_session_maker() as session:
        repo = PostgresTicketRepository(session)
        classifier = SmartRuleBasedClassifier()
        use_case = IngestTicketUseCase(repository=repo, classifier=classifier)

        # 1. Ingest realistic billing ticket
        ticket = await use_case.execute(
            content="I was billed twice on my Visa card for the monthly subscription. Please refund!",
            channel=TicketChannel.WEB,
            customer_email="john.doe@example.com",
            external_id="PG-TEST-001",
        )
        await session.commit()

        assert ticket.id is not None
        assert ticket.classification is not None
        assert ticket.classification.category.value == "billing"

        # 2. Query back by primary key
        fetched = await repo.get_by_id(ticket.id)
        assert fetched is not None
        assert fetched.id == ticket.id
        assert fetched.classification is not None
        assert fetched.classification.category.value == "billing"

        # 3. Test idempotency against Postgres
        duplicate = await use_case.execute(
            content="Duplicate call should return existing",
            channel=TicketChannel.WEB,
            external_id="PG-TEST-001",
        )
        assert duplicate.id == ticket.id

        # 4. Test analytics query with real SQL GROUP BY & AVG aggregations
        analytics_case = GetAnalyticsUseCase(repository=repo)
        summary = await analytics_case.execute()
        assert summary.total_tickets >= 1
        assert "billing" in summary.by_category
        assert summary.avg_confidence > 0.0
