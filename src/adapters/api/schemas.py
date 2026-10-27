import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

from src.domain.enums import (
    TicketChannel,
    TicketStatus,
    TicketCategory,
    Sentiment,
    Urgency,
)


class TicketCreateRequest(BaseModel):
    content: str = Field(..., min_length=5, description="Raw content of customer support message")
    channel: TicketChannel = Field(default=TicketChannel.WEB, description="Source intake channel")
    customer_email: Optional[str] = Field(default=None, description="Optional customer email")
    external_id: Optional[str] = Field(default=None, description="External CRM reference ID for idempotency")


class ClassificationResponse(BaseModel):
    id: uuid.UUID
    category: TicketCategory
    sentiment: Sentiment
    urgency: Urgency
    confidence_score: float
    model_name: str
    processed_at: datetime


class TicketResponse(BaseModel):
    id: uuid.UUID
    channel: TicketChannel
    content: str
    status: TicketStatus
    external_id: Optional[str] = None
    customer_email: Optional[str] = None
    created_at: datetime
    classification: Optional[ClassificationResponse] = None


class AnalyticsSummaryResponse(BaseModel):
    total_tickets: int
    by_category: dict[str, int]
    by_sentiment: dict[str, int]
    by_urgency: dict[str, int]
    avg_confidence: float


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    database: str = "connected"
