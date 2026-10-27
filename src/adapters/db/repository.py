from typing import Optional
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities import Ticket, TicketClassification
from src.domain.enums import TicketStatus
from src.ports.repository import TicketRepositoryPort, AnalyticsSummary
from src.adapters.db.models import TicketModel, TicketClassificationModel


def _model_to_domain(model: TicketModel) -> Ticket:
    classification = None
    if model.classification:
        classification = TicketClassification(
            id=model.classification.id,
            ticket_id=model.classification.ticket_id,
            category=model.classification.category,
            sentiment=model.classification.sentiment,
            urgency=model.classification.urgency,
            confidence_score=float(model.classification.confidence_score),
            model_name=model.classification.model_name,
            processed_at=model.classification.processed_at,
        )

    return Ticket(
        id=model.id,
        channel=model.channel,
        content=model.content,
        external_id=model.external_id,
        customer_email=model.customer_email,
        status=model.status,
        created_at=model.created_at,
        classification=classification,
    )


class PostgresTicketRepository(TicketRepositoryPort):
    """PostgreSQL adapter implementing TicketRepositoryPort via SQLAlchemy 2.0."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, ticket: Ticket) -> Ticket:
        # Construct TicketModel
        ticket_model = TicketModel(
            id=ticket.id,
            external_id=ticket.external_id,
            channel=ticket.channel,
            customer_email=ticket.customer_email,
            content=ticket.content,
            status=ticket.status,
            created_at=ticket.created_at,
        )

        if ticket.classification:
            classification_model = TicketClassificationModel(
                id=ticket.classification.id,
                ticket_id=ticket.id,
                category=ticket.classification.category,
                sentiment=ticket.classification.sentiment,
                urgency=ticket.classification.urgency,
                confidence_score=ticket.classification.confidence_score,
                model_name=ticket.classification.model_name,
                processed_at=ticket.classification.processed_at,
            )
            ticket_model.classification = classification_model

        self.session.add(ticket_model)
        await self.session.flush()
        return _model_to_domain(ticket_model)

    async def get_by_id(self, ticket_id: uuid.UUID) -> Optional[Ticket]:
        stmt = (
            select(TicketModel)
            .options(selectinload(TicketModel.classification))
            .where(TicketModel.id == ticket_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_domain(model) if model else None

    async def get_by_external_id(self, external_id: str) -> Optional[Ticket]:
        stmt = (
            select(TicketModel)
            .options(selectinload(TicketModel.classification))
            .where(TicketModel.external_id == external_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_domain(model) if model else None

    async def list_tickets(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[TicketStatus] = None,
    ) -> list[Ticket]:
        stmt = (
            select(TicketModel)
            .options(selectinload(TicketModel.classification))
            .order_by(TicketModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(TicketModel.status == status)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_model_to_domain(m) for m in models]

    async def get_analytics_summary(self) -> AnalyticsSummary:
        # 1. Total count
        total_stmt = select(func.count(TicketModel.id))
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar_one() or 0

        # 2. Aggregations by category
        cat_stmt = select(
            TicketClassificationModel.category,
            func.count(TicketClassificationModel.id),
        ).group_by(TicketClassificationModel.category)
        cat_res = await self.session.execute(cat_stmt)
        by_category = {str(row[0].value): row[1] for row in cat_res.all()}

        # 3. Aggregations by sentiment
        sent_stmt = select(
            TicketClassificationModel.sentiment,
            func.count(TicketClassificationModel.id),
        ).group_by(TicketClassificationModel.sentiment)
        sent_res = await self.session.execute(sent_stmt)
        by_sentiment = {str(row[0].value): row[1] for row in sent_res.all()}

        # 4. Aggregations by urgency
        urg_stmt = select(
            TicketClassificationModel.urgency,
            func.count(TicketClassificationModel.id),
        ).group_by(TicketClassificationModel.urgency)
        urg_res = await self.session.execute(urg_stmt)
        by_urgency = {str(row[0].value): row[1] for row in urg_res.all()}

        # 5. Average confidence
        avg_stmt = select(func.avg(TicketClassificationModel.confidence_score))
        avg_res = await self.session.execute(avg_stmt)
        avg_raw = avg_res.scalar_one()
        avg_confidence = round(float(avg_raw), 2) if avg_raw is not None else 0.0

        return AnalyticsSummary(
            total_tickets=total,
            by_category=by_category,
            by_sentiment=by_sentiment,
            by_urgency=by_urgency,
            avg_confidence=avg_confidence,
        )
