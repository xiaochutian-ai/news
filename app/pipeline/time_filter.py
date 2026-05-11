from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.models import NormalizedArticle

DEFAULT_TIME_STRATEGIES = ["source_day"]
TIME_STRATEGY_OPTIONS = [
    {"key": "source_day", "label": "来源日"},
    {"key": "source_window", "label": "来源窗口"},
    {"key": "recent_24h", "label": "近 24 小时"},
]


def normalize_time_strategies(strategies: list[str] | None) -> list[str]:
    if strategies is None:
        strategies = DEFAULT_TIME_STRATEGIES

    normalized: list[str] = []
    seen: set[str] = set()
    valid_keys = {item["key"] for item in TIME_STRATEGY_OPTIONS}
    for strategy in strategies:
        key = strategy.strip()
        if not key or key == "none" or key not in valid_keys or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _build_source_window(source_day: date, window_start: str, window_end: str) -> tuple[datetime, datetime]:
    start_time = time.fromisoformat(window_start)
    end_time = time.fromisoformat(window_end)
    return (
        datetime.combine(source_day, start_time),
        datetime.combine(source_day, end_time),
    )


def _matches_source_day(article: NormalizedArticle, *, source_day: date) -> bool:
    return article.published_at.date() == source_day


def _matches_source_window(
    article: NormalizedArticle,
    *,
    source_window: tuple[datetime, datetime],
) -> bool:
    start_at, end_at = source_window
    return start_at <= article.published_at <= end_at


def _matches_recent_24h(article: NormalizedArticle, *, digest_day: date) -> bool:
    digest_start = datetime.combine(digest_day, time.min)
    return digest_start - timedelta(hours=24) <= article.published_at < digest_start


def filter_articles_by_time(
    articles: list[NormalizedArticle],
    *,
    source_date: str,
    digest_date: str,
    strategies: list[str] | None,
    window_start: str,
    window_end: str,
) -> list[NormalizedArticle]:
    normalized_strategies = normalize_time_strategies(strategies)
    if not normalized_strategies:
        return articles

    source_day = date.fromisoformat(source_date)
    digest_day = date.fromisoformat(digest_date)
    source_window = _build_source_window(source_day, window_start, window_end)

    filtered: list[NormalizedArticle] = []
    for article in articles:
        checks: list[bool] = []
        for strategy in normalized_strategies:
            if strategy == "source_day":
                checks.append(_matches_source_day(article, source_day=source_day))
            elif strategy == "source_window":
                checks.append(_matches_source_window(article, source_window=source_window))
            elif strategy == "recent_24h":
                checks.append(_matches_recent_24h(article, digest_day=digest_day))
        if all(checks):
            filtered.append(article)
    return filtered
