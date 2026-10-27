from enum import StrEnum


class TicketChannel(StrEnum):
    EMAIL = "email"
    WEB = "web"
    TELEGRAM = "telegram"
    CRM = "crm"


class TicketStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class TicketCategory(StrEnum):
    BILLING = "billing"
    TECHNICAL_ISSUE = "technical_issue"
    ACCOUNT_ACCESS = "account_access"
    GENERAL_FEEDBACK = "general_feedback"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Urgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
