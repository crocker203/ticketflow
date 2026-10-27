import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.session import get_db_session
from src.adapters.db.repository import PostgresTicketRepository
from src.adapters.classifier.classifier import create_classifier
from src.services.ingest_ticket import IngestTicketUseCase
from src.services.analytics import GetAnalyticsUseCase, GetTicketUseCase
from src.domain.enums import TicketStatus
from src.adapters.api.schemas import (
    TicketCreateRequest,
    TicketResponse,
    AnalyticsSummaryResponse,
    HealthResponse,
)
from src.config import settings

router = APIRouter()


def get_repository(session: AsyncSession = Depends(get_db_session)) -> PostgresTicketRepository:
    return PostgresTicketRepository(session)


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        database="connected",
    )


@router.post(
    "/api/v1/tickets/webhook",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest customer ticket via webhook",
    description="Accepts support request, runs automated categorization/sentiment/urgency analysis, and persists it.",
    tags=["Tickets"],
)
async def ingest_ticket(
    payload: TicketCreateRequest,
    repo: PostgresTicketRepository = Depends(get_repository),
):
    classifier = create_classifier()
    use_case = IngestTicketUseCase(repository=repo, classifier=classifier)

    ticket = await use_case.execute(
        content=payload.content,
        channel=payload.channel,
        customer_email=payload.customer_email,
        external_id=payload.external_id,
    )
    return ticket


@router.get(
    "/api/v1/tickets",
    response_model=list[TicketResponse],
    summary="List tickets",
    description="Paginated list of support tickets with optional status filtering.",
    tags=["Tickets"],
)
async def list_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[TicketStatus] = Query(default=None),
    repo: PostgresTicketRepository = Depends(get_repository),
):
    use_case = GetTicketUseCase(repository=repo)
    return await use_case.list_all(limit=limit, offset=offset, status=status)


@router.get(
    "/api/v1/tickets/{ticket_id}",
    response_model=TicketResponse,
    summary="Get ticket by ID",
    description="Retrieve details and classification for a specific ticket.",
    tags=["Tickets"],
)
async def get_ticket(
    ticket_id: uuid.UUID,
    repo: PostgresTicketRepository = Depends(get_repository),
):
    use_case = GetTicketUseCase(repository=repo)
    ticket = await use_case.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    return ticket


@router.get(
    "/api/v1/analytics/summary",
    response_model=AnalyticsSummaryResponse,
    summary="BI Analytics Summary",
    description="Returns aggregated metrics for Superset, Metabase, Qlik, or internal dashboards.",
    tags=["Analytics"],
)
async def get_analytics_summary(
    repo: PostgresTicketRepository = Depends(get_repository),
):
    use_case = GetAnalyticsUseCase(repository=repo)
    summary = await use_case.execute()
    return summary
