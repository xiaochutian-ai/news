from __future__ import annotations

from app.models import NormalizedArticle


def _normalize_title(value: str) -> str:
    return "".join(value.split()).lower()


def _normalize_url(value: str) -> str:
    return value.strip().lower().rstrip("/")


def _deduplicate_with_key_builders(
    articles: list[NormalizedArticle],
    key_builders: list[callable],
) -> list[NormalizedArticle]:
    winners: dict[str, NormalizedArticle] = {}
    for article in articles:
        keys = [key for builder in key_builders if (key := builder(article))]
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


def _title_key(article: NormalizedArticle) -> str:
    return f"title:{_normalize_title(article.title)}"


def _url_key(article: NormalizedArticle) -> str:
    normalized = _normalize_url(article.url)
    return f"url:{normalized}" if normalized else ""


def _source_id_key(article: NormalizedArticle) -> str:
    return f"source:{article.source}:{article.source_id}"


def _deduplicate_conservative(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    return _deduplicate_with_key_builders(articles, [_title_key, _url_key])


def _deduplicate_standard(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    return _deduplicate_with_key_builders(articles, [_title_key, _url_key, _source_id_key])


def _deduplicate_aggressive(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    return _deduplicate_with_key_builders(articles, [_title_key, _url_key, _source_id_key])


def deduplicate_articles(
    articles: list[NormalizedArticle],
    strategy: str = "standard",
) -> list[NormalizedArticle]:
    if strategy == "conservative":
        return _deduplicate_conservative(articles)
    if strategy == "aggressive":
        return _deduplicate_aggressive(articles)
    return _deduplicate_standard(articles)
