from typing import Optional
import uuid
from src.domain.entities import Ticket
from src.domain.enums import TicketStatus
from src.ports.repository import TicketRepositoryPort, AnalyticsSummary


class GetAnalyticsUseCase:
    """Use case: Compute and return high-level analytics for BI / dashboard consumers."""

    def __init__(self, repository: TicketRepositoryPort) -> None:
        self.repository = repository

    async def execute(self) -> AnalyticsSummary:
        return await self.repository.get_analytics_summary()


class GetTicketUseCase:
    """Use case: Query tickets by ID or list tickets with optional filtering."""

    def __init__(self, repository: TicketRepositoryPort) -> None:
        self.repository = repository

    async def get_by_id(self, ticket_id: uuid.UUID) -> Optional[Ticket]:
        return await self.repository.get_by_id(ticket_id)

    async def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[TicketStatus] = None,
    ) -> list[Ticket]:
        return await self.repository.list_tickets(
            limit=limit,
            offset=offset,
            status=status,
        )
