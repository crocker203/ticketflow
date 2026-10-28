import pytest
import uuid
from typing import Optional

from src.domain.entities import Ticket, TicketClassification
from src.domain.enums import (
    TicketChannel,
    TicketStatus,
    TicketCategory,
    Sentiment,
    Urgency,
)
from src.ports.classifier import ClassifierPort, ClassificationResult
from src.ports.repository import TicketRepositoryPort, AnalyticsSummary
from src.services.ingest_ticket import IngestTicketUseCase
from src.services.analytics import GetAnalyticsUseCase


class InMemoryTicketRepository(TicketRepositoryPort):
    def __init__(self) -> None:
        self.tickets: dict[uuid.UUID, Ticket] = {}

    async def save(self, ticket: Ticket) -> Ticket:
        self.tickets[ticket.id] = ticket
        return ticket

    async def get_by_id(self, ticket_id: uuid.UUID) -> Optional[Ticket]:
        return self.tickets.get(ticket_id)

    async def get_by_external_id(self, external_id: str) -> Optional[Ticket]:
        for ticket in self.tickets.values():
            if ticket.external_id == external_id:
                return ticket
        return None

    async def list_tickets(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[TicketStatus] = None,
    ) -> list[Ticket]:
        results = list(self.tickets.values())
        if status:
            results = [t for t in results if t.status == status]
        return results[offset : offset + limit]

    async def get_analytics_summary(self) -> AnalyticsSummary:
        by_category: dict[str, int] = {}
        by_sentiment: dict[str, int] = {}
        by_urgency: dict[str, int] = {}
        total = len(self.tickets)
        conf_sum = 0.0
        classified_count = 0

        for t in self.tickets.values():
            if t.classification:
                classified_count += 1
                c = t.classification
                by_category[c.category.value] = by_category.get(c.category.value, 0) + 1
                by_sentiment[c.sentiment.value] = by_sentiment.get(c.sentiment.value, 0) + 1
                by_urgency[c.urgency.value] = by_urgency.get(c.urgency.value, 0) + 1
                conf_sum += c.confidence_score

        avg_conf = round(conf_sum / classified_count, 2) if classified_count > 0 else 0.0

        return AnalyticsSummary(
            total_tickets=total,
            by_category=by_category,
            by_sentiment=by_sentiment,
            by_urgency=by_urgency,
            avg_confidence=avg_conf,
        )


class MockClassifier(ClassifierPort):
    def __init__(
        self,
        category: TicketCategory = TicketCategory.BILLING,
        sentiment: Sentiment = Sentiment.NEGATIVE,
        urgency: Urgency = Urgency.HIGH,
        confidence: float = 0.95,
    ) -> None:
        self.category = category
        self.sentiment = sentiment
        self.urgency = urgency
        self.confidence = confidence
        self.call_count = 0

    async def classify(self, content: str) -> ClassificationResult:
        self.call_count += 1
        return ClassificationResult(
            category=self.category,
            sentiment=self.sentiment,
            urgency=self.urgency,
            confidence_score=self.confidence,
            model_name="mock-test-model",
        )


@pytest.mark.asyncio
async def test_ingest_ticket_flow():
    repo = InMemoryTicketRepository()
    classifier = MockClassifier()
    use_case = IngestTicketUseCase(repository=repo, classifier=classifier)

    ticket = await use_case.execute(
        content="I was double charged for my monthly subscription! Please refund.",
        channel=TicketChannel.WEB,
        customer_email="alice@example.com",
        external_id="CRM-1001",
    )

    assert ticket.id is not None
    assert ticket.channel == TicketChannel.WEB
    assert ticket.status == TicketStatus.NEW
    assert ticket.classification is not None
    assert ticket.classification.category == TicketCategory.BILLING
    assert ticket.classification.urgency == Urgency.HIGH
    assert classifier.call_count == 1

    # Verify persisted in repository
    found = await repo.get_by_id(ticket.id)
    assert found == ticket


@pytest.mark.asyncio
async def test_ingest_ticket_idempotency():
    repo = InMemoryTicketRepository()
    classifier = MockClassifier()
    use_case = IngestTicketUseCase(repository=repo, classifier=classifier)

    # First delivery
    first_ticket = await use_case.execute(
        content="Same message",
        channel=TicketChannel.CRM,
        external_id="WEBHOOK-UNIQUE-99",
    )

    # Duplicate delivery (e.g. network retry)
    duplicate_ticket = await use_case.execute(
        content="Same message duplicate",
        channel=TicketChannel.CRM,
        external_id="WEBHOOK-UNIQUE-99",
    )

    assert first_ticket.id == duplicate_ticket.id
    # Classifier should only have been called ONCE due to idempotency
    assert classifier.call_count == 1


@pytest.mark.asyncio
async def test_analytics_summary_calculation():
    repo = InMemoryTicketRepository()
    classifier = MockClassifier(category=TicketCategory.TECHNICAL_ISSUE)
    use_case = IngestTicketUseCase(repository=repo, classifier=classifier)

    await use_case.execute(content="Bug in payment screen", channel=TicketChannel.WEB)
    await use_case.execute(content="500 server error on login", channel=TicketChannel.EMAIL)

    analytics_case = GetAnalyticsUseCase(repository=repo)
    summary = await analytics_case.execute()

    assert summary.total_tickets == 2
    assert summary.by_category.get("technical_issue") == 2
    assert summary.avg_confidence == 0.95
