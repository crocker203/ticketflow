from typing import Protocol, Optional
from dataclasses import dataclass
import uuid

from src.domain.entities import Ticket
from src.domain.enums import TicketStatus


@dataclass(frozen=True)
class AnalyticsSummary:
    total_tickets: int
    by_category: dict[str, int]
    by_sentiment: dict[str, int]
    by_urgency: dict[str, int]
    avg_confidence: float


class TicketRepositoryPort(Protocol):
    """Abstract repository port for persisting and querying tickets and classifications.

    Allows plugging in PostgreSQL (SQLAlchemy), In-Memory test repos, or other databases
    without touching core business use cases.
    """

    async def save(self, ticket: Ticket) -> Ticket:
        """Persist a ticket and its associated classification."""
        ...

    async def get_by_id(self, ticket_id: uuid.UUID) -> Optional[Ticket]:
        """Retrieve a ticket by its primary key ID."""
        ...

    async def get_by_external_id(self, external_id: str) -> Optional[Ticket]:
        """Find an existing ticket by external CRM ID (for idempotency)."""
        ...

    async def list_tickets(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[TicketStatus] = None,
    ) -> list[Ticket]:
        """Paginated list of tickets, optionally filtered by status."""
        ...

    async def get_analytics_summary(self) -> AnalyticsSummary:
        """Compute aggregated analytics metrics across all tickets and classifications."""
        ...
