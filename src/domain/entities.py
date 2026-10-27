from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Optional

from src.domain.enums import (
    TicketChannel,
    TicketStatus,
    TicketCategory,
    Sentiment,
    Urgency,
)
from src.domain.id import generate_uuid7


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(kw_only=True)
class TicketClassification:
    id: uuid.UUID = field(default_factory=generate_uuid7)
    ticket_id: uuid.UUID
    category: TicketCategory
    sentiment: Sentiment
    urgency: Urgency
    confidence_score: float
    model_name: str
    processed_at: datetime = field(default_factory=utc_now)


@dataclass(kw_only=True)
class Ticket:
    id: uuid.UUID = field(default_factory=generate_uuid7)
    channel: TicketChannel
    content: str
    external_id: Optional[str] = None
    customer_email: Optional[str] = None
    status: TicketStatus = TicketStatus.NEW
    created_at: datetime = field(default_factory=utc_now)
    classification: Optional[TicketClassification] = None
