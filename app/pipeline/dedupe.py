from __future__ import annotations

from app.models import NormalizedArticle


def _normalize_title(value: str) -> str:
    return "".join(value.split()).lower()


def _normalize_url(value: str) -> str:
    return value.strip().lower().rstrip("/")


def deduplicate_articles(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    winners: dict[str, NormalizedArticle] = {}
    for article in articles:
        keys = [
            f"title:{_normalize_title(article.title)}",
            f"url:{_normalize_url(article.url)}",
            f"source:{article.source}:{article.source_id}",
        ]
        matched_key = next((key for key in keys if key in winners), None)
        if matched_key is None:
            for key in keys:
                winners[key] = article
            continue

        current = winners[matched_key]
        preferred = article if article.score >= current.score else current
        for key in keys:
            winners[key] = preferred
        existing_keys = [key for key, item in winners.items() if item is current]
        for key in existing_keys:
            winners[key] = preferred

    unique: list[NormalizedArticle] = []
    seen_ids: set[int] = set()
    for article in winners.values():
        marker = id(article)
        if marker in seen_ids:
            continue
        seen_ids.add(marker)
        unique.append(article)
    return unique
