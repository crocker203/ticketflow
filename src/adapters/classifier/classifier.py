import re
import httpx
from typing import Optional

from src.domain.enums import TicketCategory, Sentiment, Urgency
from src.ports.classifier import ClassifierPort, ClassificationResult
from src.config import settings


class SmartRuleBasedClassifier(ClassifierPort):
    """Zero-dependency smart heuristic classifier for local dev, offline demos, and CI/CD.

    Evaluates keyword frequency, sentiment signals, and urgency indicators.
    """

    BILLING_PATTERNS = [
        r"refund", r"charg(e|ed|ing)", r"bill(ing)?", r"invoic(e|ed)?",
        r"payment", r"card", r"subscription", r"money", r"price", r"cost"
    ]
    TECH_PATTERNS = [
        r"bug", r"error", r"500", r"404", r"crash(ed)?", r"not working",
        r"broken", r"failed", r"exception", r"stack trace", r"glitch", r"down"
    ]
    ACCESS_PATTERNS = [
        r"password", r"login", r"log in", r"sign in", r"auth(entication)?",
        r"account", r"locked", r"reset", r"2fa", r"otp", r"token"
    ]

    NEGATIVE_SIGNALS = [
        r"terrible", r"horrible", r"worst", r"angry", r"broken",
        r"fail", r"hate", r"unacceptable", r"scam", r"lawyer", r"fraud"
    ]
    POSITIVE_SIGNALS = [
        r"thank(s)?", r"great", r"good", r"love", r"appreciate",
        r"awesome", r"helpful", r"excellent", r"kudos"
    ]
    CRITICAL_SIGNALS = [
        r"urgent", r"immediately", r"asap", r"emergency", r"critical",
        r"production down", r"cannot operate", r"outage", r"lawsuit"
    ]

    async def classify(self, content: str) -> ClassificationResult:
        text = content.lower()

        # 1. Category Detection
        billing_hits = sum(1 for p in self.BILLING_PATTERNS if re.search(r"\b" + p, text))
        tech_hits = sum(1 for p in self.TECH_PATTERNS if re.search(r"\b" + p, text))
        access_hits = sum(1 for p in self.ACCESS_PATTERNS if re.search(r"\b" + p, text))

        max_hits = max(billing_hits, tech_hits, access_hits)
        if max_hits == 0:
            category = TicketCategory.GENERAL_FEEDBACK
            confidence = 0.75
        elif max_hits == billing_hits:
            category = TicketCategory.BILLING
            confidence = min(0.85 + (0.04 * billing_hits), 0.98)
        elif max_hits == tech_hits:
            category = TicketCategory.TECHNICAL_ISSUE
            confidence = min(0.85 + (0.04 * tech_hits), 0.98)
        else:
            category = TicketCategory.ACCOUNT_ACCESS
            confidence = min(0.85 + (0.04 * access_hits), 0.98)

        # 2. Sentiment Detection
        neg_count = sum(1 for p in self.NEGATIVE_SIGNALS if re.search(r"\b" + p, text))
        pos_count = sum(1 for p in self.POSITIVE_SIGNALS if re.search(r"\b" + p, text))

        if neg_count > pos_count:
            sentiment = Sentiment.NEGATIVE
        elif pos_count > neg_count:
            sentiment = Sentiment.POSITIVE
        else:
            sentiment = Sentiment.NEUTRAL

        # 3. Urgency Detection
        critical_count = sum(1 for p in self.CRITICAL_SIGNALS if re.search(r"\b" + p, text))
        if critical_count > 0:
            urgency = Urgency.CRITICAL
        elif sentiment == Sentiment.NEGATIVE or category == TicketCategory.BILLING:
            urgency = Urgency.HIGH
        elif category == TicketCategory.TECHNICAL_ISSUE:
            urgency = Urgency.MEDIUM
        else:
            urgency = Urgency.LOW

        return ClassificationResult(
            category=category,
            sentiment=sentiment,
            urgency=urgency,
            confidence_score=round(confidence, 2),
            model_name="smart-heuristic-v1",
        )


class OpenAIClassifier(ClassifierPort):
    """External LLM adapter using OpenAI-compatible Chat Completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    async def classify(self, content: str) -> ClassificationResult:
        # Prompt instructing structured JSON output
        prompt = (
            "Analyze this customer support ticket. Return valid JSON only with keys: "
            "'category' (billing|technical_issue|account_access|general_feedback), "
            "'sentiment' (positive|neutral|negative), "
            "'urgency' (low|medium|high|critical), "
            "'confidence' (float between 0.0 and 1.0).\n\n"
            f"Ticket: \"{content}\""
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a customer support ticket classification engine."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            import json
            parsed = json.loads(data["choices"][0]["message"]["content"])
            return ClassificationResult(
                category=TicketCategory(parsed["category"]),
                sentiment=Sentiment(parsed["sentiment"]),
                urgency=Urgency(parsed["urgency"]),
                confidence_score=float(parsed["confidence"]),
                model_name=self.model,
            )


def create_classifier() -> ClassifierPort:
    """Factory to create appropriate classifier adapter based on application config."""
    if settings.CLASSIFIER_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAIClassifier(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    return SmartRuleBasedClassifier()
