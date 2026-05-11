from __future__ import annotations

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


def _combined_text(article: NormalizedArticle) -> str:
    return f"{article.title} {article.summary} {article.content}"


def _positive_keyword_hits(article: NormalizedArticle) -> int:
    combined = _combined_text(article)
    return sum(1 for keyword in POSITIVE_KEYWORDS if keyword in combined)


def _negative_keyword_hits(article: NormalizedArticle) -> int:
    combined = _combined_text(article)
    return sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in combined)


def _filter_loose_articles(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    filtered: list[NormalizedArticle] = []
    for article in articles:
        if any(tag in POSITIVE_TAGS for tag in article.tags):
            filtered.append(article)
            continue
        if _positive_keyword_hits(article) > 0:
            filtered.append(article)
    return filtered


def _filter_standard_articles(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    filtered: list[NormalizedArticle] = []
    for article in articles:
        if any(tag in POSITIVE_TAGS for tag in article.tags):
            filtered.append(article)
            continue
        if _positive_keyword_hits(article) > 0:
            filtered.append(article)
            continue
        if _negative_keyword_hits(article) > 0:
            continue
    return filtered


def _filter_strict_articles(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    filtered: list[NormalizedArticle] = []
    for article in articles:
        if _negative_keyword_hits(article) > 0:
            continue
        if any(tag in POSITIVE_TAGS for tag in article.tags):
            filtered.append(article)
            continue
        if _positive_keyword_hits(article) >= 2:
            filtered.append(article)
    return filtered


def filter_articles(
    articles: list[NormalizedArticle],
    strategy: str = "standard",
    *,
    time_strategies: list[str] | None = None,
    source_date: str | None = None,
    digest_date: str | None = None,
    window_start: str = "19:30",
    window_end: str = "22:30",
) -> list[NormalizedArticle]:
    filtered: list[NormalizedArticle]
    if strategy == "loose":
        filtered = _filter_loose_articles(articles)
    elif strategy == "strict":
        filtered = _filter_strict_articles(articles)
    else:
        filtered = _filter_standard_articles(articles)

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
