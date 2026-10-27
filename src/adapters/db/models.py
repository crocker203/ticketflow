import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    Text,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.domain.enums import (
    TicketChannel,
    TicketStatus,
    TicketCategory,
    Sentiment,
    Urgency,
)


class Base(DeclarativeBase):
    pass


class TicketModel(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    channel: Mapped[TicketChannel] = mapped_column(
        SAEnum(TicketChannel, name="ticket_channel", native_enum=True),
        nullable=False,
    )
    customer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status", native_enum=True),
        nullable=False,
        default=TicketStatus.NEW,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # 1:1 relationship to classification result
    classification: Mapped["TicketClassificationModel | None"] = relationship(
        "TicketClassificationModel",
        back_populates="ticket",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_tickets_status_created", "status", "created_at"),
    )


class TicketClassificationModel(Base):
    __tablename__ = "ticket_classifications"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    category: Mapped[TicketCategory] = mapped_column(
        SAEnum(TicketCategory, name="ticket_category", native_enum=True),
        nullable=False,
    )
    sentiment: Mapped[Sentiment] = mapped_column(
        SAEnum(Sentiment, name="ticket_sentiment", native_enum=True),
        nullable=False,
    )
    urgency: Mapped[Urgency] = mapped_column(
        SAEnum(Urgency, name="ticket_urgency", native_enum=True),
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ticket: Mapped["TicketModel"] = relationship(
        "TicketModel",
        back_populates="classification",
    )

    __table_args__ = (
        Index("idx_classifications_cat_sent", "category", "sentiment"),
    )
