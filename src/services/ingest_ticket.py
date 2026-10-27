from typing import Optional
from src.domain.entities import Ticket, TicketClassification
from src.domain.enums import TicketChannel
from src.ports.repository import TicketRepositoryPort
from src.ports.classifier import ClassifierPort


class IngestTicketUseCase:
    """Use case: Receive an incoming support request, classify it, and persist it."""

    def __init__(
        self,
        repository: TicketRepositoryPort,
        classifier: ClassifierPort,
    ) -> None:
        self.repository = repository
        self.classifier = classifier

    async def execute(
        self,
        content: str,
        channel: TicketChannel,
        customer_email: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> Ticket:
        # 1. Idempotency check: if external_id is provided and already exists, return existing
        if external_id:
            existing = await self.repository.get_by_external_id(external_id)
            if existing:
                return existing

        # 2. Instantiate new ticket
        ticket = Ticket(
            channel=channel,
            content=content,
            customer_email=customer_email,
            external_id=external_id,
        )

        # 3. Perform automated classification via the classifier port
        result = await self.classifier.classify(content)

        # 4. Construct classification entity linked to the ticket
        classification = TicketClassification(
            ticket_id=ticket.id,
            category=result.category,
            sentiment=result.sentiment,
            urgency=result.urgency,
            confidence_score=result.confidence_score,
            model_name=result.model_name,
        )
        ticket.classification = classification

        # 5. Persist ticket and classification in the repository
        saved_ticket = await self.repository.save(ticket)
        return saved_ticket
