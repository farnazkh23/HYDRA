from __future__ import annotations

import asyncio
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Iterable

from backend.models import KYCProfile, RawSignal, SignalType


EVENT_REGISTRY_BASE = "https://eventregistry.org/api/v1"
ADVERSE_QUERY_TERMS = [
    "investigation",
    "lawsuit",
    "regulatory investigation",
    "export control",
    "governance",
    "offshore",
]

ADVERSE_KEYWORDS = [
    "fraud",
    "investigation",
    "arrest",
    "money laundering",
    "bribery",
    "corruption",
    "lawsuit",
    "indictment",
    "bankruptcy",
    "regulatory action",
    "fine",
    "penalty",
    "compliance failure",
    "adverse",
    "scandal",
    "seized",
    "frozen assets",
    "criminal",
    "crypto exchange",
    "offshore",
    "beneficial owner",
    "shell company",
]


class EventRegistryNewsCollector:
    """News collector that emits shared RawSignal objects for HYDRA Loop A."""

    def __init__(
        self,
        api_key: str | None = None,
        enabled: bool | None = None,
        expand_adverse_queries: bool = False,
    ) -> None:
        self.api_key = api_key or os.getenv("EVENT_REGISTRY_API_KEY")
        self.enabled = bool(self.api_key) if enabled is None else enabled
        self.expand_adverse_queries = expand_adverse_queries
        self.last_query_count = 0

    def fetch_company_news(self, client_id: str, company_name: str, limit: int = 10) -> list[RawSignal]:
        if not self.enabled:
            self.last_query_count = 0
            return list(mock_company_news(client_id, company_name))[:limit]

        signals: list[RawSignal] = []
        self.last_query_count = 0
        for query in _expanded_news_queries(company_name, self.expand_adverse_queries):
            params = urllib.parse.urlencode(
                {
                    "apiKey": self.api_key,
                    "keyword": query,
                    "articlesSortBy": "date",
                    "articlesCount": limit,
                    "resultType": "articles",
                    "lang": "eng",
                }
            )
            url = f"{EVENT_REGISTRY_BASE}/article/getArticles?{params}"
            try:
                with urllib.request.urlopen(url, timeout=8) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except Exception:
                return list(mock_company_news(client_id, company_name))[:limit]

            self.last_query_count += 1
            signals.extend(
                _article_payload_to_signals(
                    payload=payload,
                    client_id=client_id,
                    company_name=company_name,
                    fallback_url=url,
                    adverse_only=query != company_name,
                    query=query,
                )
            )
        signals = dedupe_signals(signals)
        return signals or list(mock_company_news(client_id, company_name))[:limit]


async def fetch_news(client: KYCProfile, days_back: int = 7) -> list[RawSignal]:
    """Async Event Registry article search for backend schedulers/API routes."""
    api_key = os.getenv("EVENT_REGISTRY_API_KEY", "")
    if not api_key:
        return list(mock_company_news(client.client_id, client.name))

    date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = datetime.utcnow().strftime("%Y-%m-%d")
    payload = {
        "apiKey": api_key,
        "action": "getArticles",
        "keyword": client.name,
        "keywordLoc": "title",
        "dateStart": date_from,
        "dateEnd": date_to,
        "articlesCount": 20,
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "resultType": "articles",
        "dataType": ["news", "blog"],
        "lang": ["eng", "deu", "fra"],
        "includeArticleTitle": True,
        "includeArticleBody": True,
        "includeArticleUrl": True,
        "includeArticleSource": True,
        "includeArticleSentiment": True,
        "includeArticleCategories": True,
    }

    data = await asyncio.to_thread(_post_json, f"{EVENT_REGISTRY_BASE}/article/getArticles", payload)
    return _article_payload_to_signals(
        payload=data,
        client_id=client.client_id,
        company_name=client.name,
        fallback_url=f"{EVENT_REGISTRY_BASE}/article/getArticles",
        adverse_only=True,
        date_range=f"{date_from} to {date_to}",
    )


async def fetch_events(client: KYCProfile, days_back: int = 7) -> list[RawSignal]:
    """Async Event Registry event-cluster search for backend schedulers/API routes."""
    api_key = os.getenv("EVENT_REGISTRY_API_KEY", "")
    if not api_key:
        return []

    date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = datetime.utcnow().strftime("%Y-%m-%d")
    payload = {
        "apiKey": api_key,
        "action": "getEvents",
        "keyword": client.name,
        "dateStart": date_from,
        "dateEnd": date_to,
        "eventsCount": 10,
        "eventsSortBy": "date",
        "resultType": "events",
        "includeEventTitle": True,
        "includeEventSummary": True,
        "includeEventArticleCounts": True,
        "includeEventCategories": True,
        "includeEventSentiment": True,
        "lang": ["eng", "deu", "fra"],
    }

    data = await asyncio.to_thread(_post_json, f"{EVENT_REGISTRY_BASE}/event/getEvents", payload)
    signals: list[RawSignal] = []
    for event in data.get("events", {}).get("results", []):
        title = _first_localized_text(event.get("title", {}))
        summary = _first_localized_text(event.get("summary", {}))
        sentiment = event.get("sentiment")
        article_count = event.get("totalArticleCount", 0)
        categories = [category.get("label", "") for category in event.get("categories", [])]
        strongly_negative = sentiment is not None and sentiment < -0.3
        if not (_is_adverse(title, summary) or strongly_negative):
            continue

        signals.append(
            RawSignal(
                entity_name=client.name,
                client_id=client.client_id,
                signal_type=SignalType.NEWS,
                source="event_registry_events",
                content=f"{title}\n\n{summary[:500]}",
                metadata={
                    "signal_id": _stable_signal_id(f"event:{title}", title),
                    "title": title,
                    "sentiment_score": sentiment,
                    "article_count": article_count,
                    "categories": categories,
                    "date_range": f"{date_from} to {date_to}",
                    "signal_strength": "high" if article_count > 10 else "medium",
                    "provider": "event_registry",
                },
            )
        )
    return signals


async def collect(client: KYCProfile, days_back: int = 7) -> list[RawSignal]:
    """Runs article and event search, then deduplicates by title."""
    articles = await fetch_news(client, days_back)
    events = await fetch_events(client, days_back)
    seen_titles: set[str] = set()
    combined: list[RawSignal] = []
    for signal in articles + events:
        title = str(signal.metadata.get("title", signal.content[:80]))
        if title in seen_titles:
            continue
        seen_titles.add(title)
        combined.append(signal)
    return combined


def mock_company_news(client_id: str, company_name: str) -> Iterable[RawSignal]:
    now = datetime.now(timezone.utc)
    samples = [
        {
            "title": f"{company_name} expands Starlink satellite service capacity",
            "summary": "The company announced additional launch capacity and satellite internet coverage improvements.",
            "url": "mock://news/spacex-starlink-expansion",
            "related_entities": ["Elon Musk"],
            "entity_roles": {"Elon Musk": "beneficial_owner_or_key_person"},
            "sentiment_score": 0.2,
        },
        {
            "title": f"{company_name} faces regulatory investigation over offshore launch-services partnership",
            "summary": f"Reports say {company_name} and Elon Musk are under review after a proposed partnership with Orbital Ventures Ltd raised export control and governance questions.",
            "url": "mock://news/spacex-offshore-investigation",
            "related_entities": ["Elon Musk", "Orbital Ventures Ltd"],
            "entity_roles": {
                "Elon Musk": "beneficial_owner_or_key_person",
                "Orbital Ventures Ltd": "partner_or_counterparty",
            },
            "sentiment_score": -0.7,
        },
        {
            "title": f"Governance lawsuit names Elon Musk in dispute linked to {company_name} financing",
            "summary": f"A shareholder lawsuit alleges governance concerns around related-party financing and {company_name} board oversight.",
            "url": "mock://news/spacex-governance-lawsuit",
            "related_entities": ["Elon Musk"],
            "entity_roles": {"Elon Musk": "beneficial_owner_or_key_person"},
            "sentiment_score": -0.45,
        },
    ]
    for sample in samples:
        yield RawSignal(
            entity_name=company_name,
            client_id=client_id,
            signal_type=SignalType.NEWS,
            source="mock_news",
            content=f"{sample['title']}\n{sample['summary']}",
            timestamp=now,
            metadata={
                "signal_id": _stable_signal_id(sample["url"], sample["title"]),
                "title": sample["title"],
                "url": sample["url"],
                "published_at": now.isoformat(),
                "provider": "mock",
                "related_entities": sample.get("related_entities", []),
                "entity_roles": sample.get("entity_roles", {}),
                "sentiment_score": sample.get("sentiment_score"),
            },
        )


def _article_payload_to_signals(
    payload: dict,
    client_id: str,
    company_name: str,
    fallback_url: str,
    adverse_only: bool,
    date_range: str | None = None,
    query: str | None = None,
) -> list[RawSignal]:
    signals: list[RawSignal] = []
    for article in payload.get("articles", {}).get("results", []):
        title = article.get("title") or "Untitled article"
        body = article.get("body") or article.get("summary") or ""
        sentiment = article.get("sentiment")
        article_url = article.get("url") or fallback_url
        source = article.get("source", {}).get("title", "EventRegistry")
        published_at = article.get("dateTime") or datetime.now(timezone.utc).isoformat()
        strongly_negative = sentiment is not None and sentiment < -0.3
        if adverse_only and not (_is_adverse(title, body) or strongly_negative):
            continue

        signals.append(
            RawSignal(
                entity_name=company_name,
                client_id=client_id,
                signal_type=SignalType.NEWS,
                source=f"event_registry/{source}",
                content=f"{title}\n{body[:1200]}",
                timestamp=_parse_datetime(published_at),
                metadata={
                    "signal_id": _stable_signal_id(article_url, title),
                    "title": title,
                    "url": article_url,
                    "published_at": published_at,
                    "sentiment_score": sentiment,
                    "date_range": date_range,
                    "query": query,
                    "provider": "event_registry",
                },
            )
        )
    return signals


def _expanded_news_queries(company_name: str, expand_adverse_queries: bool) -> list[str]:
    if not expand_adverse_queries:
        return [company_name]
    return [company_name, *[f"{company_name} {term}" for term in ADVERSE_QUERY_TERMS]]


def dedupe_signals(signals: list[RawSignal]) -> list[RawSignal]:
    seen: set[str] = set()
    deduped: list[RawSignal] = []
    for signal in signals:
        title = str(signal.metadata.get("title", "")).strip().lower()
        url = str(signal.metadata.get("url", "")).strip().lower()
        keys = [key for key in (url, title) if key]
        if not keys or any(key in seen for key in keys):
            continue
        seen.update(keys)
        deduped.append(signal)
    return deduped


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _is_adverse(title: str, body: str) -> bool:
    text = f"{title} {body}".lower()
    return any(keyword in text for keyword in ADVERSE_KEYWORDS)


def _first_localized_text(value: dict) -> str:
    if not value:
        return ""
    return value.get("eng", "") or next(iter(value.values()), "")


def _stable_signal_id(url: str, title: str) -> str:
    digest = hashlib.sha256(f"{url}:{title}".encode("utf-8")).hexdigest()
    return f"sig_{digest[:16]}"


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
