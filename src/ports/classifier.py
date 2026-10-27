from typing import Protocol
from dataclasses import dataclass
from src.domain.enums import TicketCategory, Sentiment, Urgency


@dataclass(frozen=True)
class ClassificationResult:
    category: TicketCategory
    sentiment: Sentiment
    urgency: Urgency
    confidence_score: float
    model_name: str


class ClassifierPort(Protocol):
    """Abstract port for ticket categorization and sentiment analysis.

    Decouples domain logic from concrete classification providers (e.g. rule-based
    heuristic engines, external ML services, or LLM providers).
    """

    async def classify(self, content: str) -> ClassificationResult:
        ...
