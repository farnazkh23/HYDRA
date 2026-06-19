import os
import httpx
from datetime import datetime, timedelta
from backend.models import KYCProfile, RawSignal, SignalType

EVENT_REGISTRY_API_KEY = os.getenv("EVENT_REGISTRY_API_KEY", "")
EVENT_REGISTRY_BASE = "https://eventregistry.org/api/v1"

# Keywords that elevate an article to a risk signal worth flagging
ADVERSE_KEYWORDS = [
    "fraud", "sanction", "investigation", "arrest", "money laundering",
    "bribery", "corruption", "lawsuit", "indictment", "bankruptcy",
    "regulatory action", "fine", "penalty", "compliance failure",
    "adverse", "scandal", "seized", "frozen assets", "criminal",
]


def _is_adverse(title: str, body: str) -> bool:
    text = (title + " " + body).lower()
    return any(kw in text for kw in ADVERSE_KEYWORDS)


async def fetch_news(client: KYCProfile, days_back: int = 7) -> list[RawSignal]:
    """
    Search Event Registry for recent articles about a KYC client.
    Returns only articles that contain adverse media signals.
    """
    if not EVENT_REGISTRY_API_KEY:
        raise EnvironmentError("EVENT_REGISTRY_API_KEY is not set")

    date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = datetime.utcnow().strftime("%Y-%m-%d")

    payload = {
        "apiKey": EVENT_REGISTRY_API_KEY,
        "action": "getArticles",
        "keyword": client.name,
        "keywordLoc": "title",           # focus on titles for precision
        "dateStart": date_from,
        "dateEnd": date_to,
        "articlesCount": 20,
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "resultType": "articles",
        "dataType": ["news", "blog"],
        "lang": ["eng", "deu", "fra"],   # English, German, French — relevant for Swiss banking
        "includeArticleTitle": True,
        "includeArticleBody": True,
        "includeArticleUrl": True,
        "includeArticleSource": True,
        "includeArticleSentiment": True, # Event Registry provides sentiment scores
        "includeArticleCategories": True,
    }

    signals: list[RawSignal] = []

    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.post(f"{EVENT_REGISTRY_BASE}/article/getArticles", json=payload)
        resp.raise_for_status()
        data = resp.json()

    articles = data.get("articles", {}).get("results", [])

    for article in articles:
        title = article.get("title", "")
        body = article.get("body", "")
        sentiment = article.get("sentiment", None)        # float: -1 (negative) to 1 (positive)
        url = article.get("url", "")
        source = article.get("source", {}).get("title", "Unknown")
        pub_date = article.get("dateTime", datetime.utcnow().isoformat())

        # Flag if explicitly adverse keywords found OR sentiment is strongly negative
        strongly_negative = sentiment is not None and sentiment < -0.3
        if not (_is_adverse(title, body) or strongly_negative):
            continue

        signals.append(RawSignal(
            entity_name=client.name,
            client_id=client.client_id,
            signal_type=SignalType.NEWS,
            source=f"EventRegistry / {source}",
            content=f"{title}\n\n{body[:500]}",
            timestamp=datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                      if isinstance(pub_date, str) else datetime.utcnow(),
            metadata={
                "url": url,
                "source": source,
                "sentiment_score": sentiment,
                "title": title,
                "date_range": f"{date_from} to {date_to}",
            },
        ))

    return signals


async def fetch_events(client: KYCProfile, days_back: int = 7) -> list[RawSignal]:
    """
    Search Event Registry for news *events* (clustered stories) about a client.
    Events are higher-signal than individual articles — they represent sustained coverage.
    """
    if not EVENT_REGISTRY_API_KEY:
        raise EnvironmentError("EVENT_REGISTRY_API_KEY is not set")

    date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = datetime.utcnow().strftime("%Y-%m-%d")

    payload = {
        "apiKey": EVENT_REGISTRY_API_KEY,
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

    signals: list[RawSignal] = []

    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.post(f"{EVENT_REGISTRY_BASE}/event/getEvents", json=payload)
        resp.raise_for_status()
        data = resp.json()

    events = data.get("events", {}).get("results", [])

    for event in events:
        title = event.get("title", {}).get("eng", "") or next(iter(event.get("title", {}).values()), "")
        summary = event.get("summary", {}).get("eng", "") or next(iter(event.get("summary", {}).values()), "")
        sentiment = event.get("sentiment", None)
        article_count = event.get("totalArticleCount", 0)
        categories = [c.get("label", "") for c in event.get("categories", [])]

        strongly_negative = sentiment is not None and sentiment < -0.3
        if not (_is_adverse(title, summary) or strongly_negative):
            continue

        signals.append(RawSignal(
            entity_name=client.name,
            client_id=client.client_id,
            signal_type=SignalType.NEWS,
            source="EventRegistry/Events",
            content=f"{title}\n\n{summary[:500]}",
            metadata={
                "title": title,
                "sentiment_score": sentiment,
                "article_count": article_count,   # how many outlets covered this
                "categories": categories,
                "date_range": f"{date_from} to {date_to}",
                "signal_strength": "high" if article_count > 10 else "medium",
            },
        ))

    return signals


async def collect(client: KYCProfile, days_back: int = 7) -> list[RawSignal]:
    """Entry point: runs both article and event search, deduplicates by title."""
    articles = await fetch_news(client, days_back)
    events = await fetch_events(client, days_back)

    seen_titles: set[str] = set()
    combined: list[RawSignal] = []
    for signal in articles + events:
        title = signal.metadata.get("title", signal.content[:80])
        if title not in seen_titles:
            seen_titles.add(title)
            combined.append(signal)

    return combined
