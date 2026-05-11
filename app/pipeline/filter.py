from __future__ import annotations

from collections.abc import Callable, Iterable

from app.models import NormalizedArticle
from app.pipeline.time_filter import filter_articles_by_time

POSITIVE_KEYWORDS = {
    "医保",
    "医疗",
    "养老",
    "就业",
    "住房",
    "小区",
    "教育",
    "交通",
    "消费",
    "食品安全",
    "社保",
    "文旅",
    "生态",
    "灾害",
    "公共服务",
    "稳就业",
    "城市更新",
    "报销",
}

POSITIVE_TAGS = {
    "医保",
    "医疗",
    "养老",
    "就业",
    "住房",
    "教育",
    "交通",
    "消费",
    "社保",
    "文旅",
    "生态",
    "公共服务",
    "民生",
}

NEGATIVE_KEYWORDS = {
    "国际会议",
    "国际局势",
    "外交",
    "外事",
    "党建",
}

DEFAULT_BLOCKED_KEYWORDS = (
    "习近平",
    "李强",
    "习主席",
    "总书记",
)

ArticlePredicate = Callable[[NormalizedArticle], bool]


def _combined_text(article: NormalizedArticle) -> str:
    return f"{article.title} {article.summary} {article.content}"


def normalize_keywords(
    keywords: Iterable[str] | None,
    *,
    default: Iterable[str] = (),
) -> tuple[str, ...]:
    source = keywords if keywords is not None else default
    normalized: list[str] = []
    seen: set[str] = set()
    for keyword in source:
        normalized_keyword = keyword.strip()
        if not normalized_keyword or normalized_keyword in seen:
            continue
        seen.add(normalized_keyword)
        normalized.append(normalized_keyword)
    return tuple(normalized)


def _keyword_hits(article: NormalizedArticle, keywords: Iterable[str]) -> int:
    combined = _combined_text(article)
    return sum(1 for keyword in keywords if keyword in combined)


def _positive_keyword_hits(article: NormalizedArticle) -> int:
    return _keyword_hits(article, POSITIVE_KEYWORDS)


def _negative_keyword_hits(article: NormalizedArticle) -> int:
    return _keyword_hits(article, NEGATIVE_KEYWORDS)


def _has_positive_tag(article: NormalizedArticle) -> bool:
    return any(tag in POSITIVE_TAGS for tag in article.tags)


def _matches_loose_strategy(article: NormalizedArticle) -> bool:
    return _has_positive_tag(article) or _positive_keyword_hits(article) > 0


def _matches_standard_strategy(article: NormalizedArticle) -> bool:
    if _has_positive_tag(article):
        return True
    if _positive_keyword_hits(article) > 0:
        return True
    if _negative_keyword_hits(article) > 0:
        return False
    return False


def _matches_strict_strategy(article: NormalizedArticle) -> bool:
    if _negative_keyword_hits(article) > 0:
        return False
    if _has_positive_tag(article):
        return True
    return _positive_keyword_hits(article) >= 2


def _build_blacklist_predicate(blocked_keywords: Iterable[str] | None) -> ArticlePredicate | None:
    normalized_keywords = normalize_keywords(
        blocked_keywords,
        default=DEFAULT_BLOCKED_KEYWORDS,
    )
    if not normalized_keywords:
        return None

    def _predicate(article: NormalizedArticle) -> bool:
        return _keyword_hits(article, normalized_keywords) == 0

    return _predicate


def _apply_predicates(
    articles: list[NormalizedArticle],
    predicates: Iterable[ArticlePredicate],
) -> list[NormalizedArticle]:
    filtered: list[NormalizedArticle] = []
    for article in articles:
        if all(predicate(article) for predicate in predicates):
            filtered.append(article)
    return filtered


def _build_strategy_predicate(strategy: str) -> ArticlePredicate:
    if strategy == "loose":
        return _matches_loose_strategy
    if strategy == "strict":
        return _matches_strict_strategy
    return _matches_standard_strategy


def filter_articles(
    articles: list[NormalizedArticle],
    strategy: str = "standard",
    *,
    blocked_keywords: Iterable[str] | None = None,
    time_strategies: list[str] | None = None,
    source_date: str | None = None,
    digest_date: str | None = None,
    window_start: str = "19:30",
    window_end: str = "22:30",
) -> list[NormalizedArticle]:
    predicates: list[ArticlePredicate] = [_build_strategy_predicate(strategy)]
    blacklist_predicate = _build_blacklist_predicate(blocked_keywords)
    if blacklist_predicate is not None:
        predicates.append(blacklist_predicate)

    filtered = _apply_predicates(articles, predicates)

    if source_date is None or digest_date is None:
        return filtered

    return filter_articles_by_time(
        filtered,
        source_date=source_date,
        digest_date=digest_date,
        strategies=time_strategies,
        window_start=window_start,
        window_end=window_end,
    )


def filter_minsheng_articles(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    return filter_articles(articles, strategy="standard")
