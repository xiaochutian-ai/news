from datetime import datetime

from app.models import NormalizedArticle
from app.pipeline.dedupe import deduplicate_articles
from app.pipeline.filter import filter_articles


def _article(
    *,
    title: str,
    summary: str = "",
    content: str = "",
    tags: list[str] | None = None,
    source: str = "xinhua",
    url: str = "https://example.com/a",
    source_id: str = "a",
    score: float = 80.0,
) -> NormalizedArticle:
    return NormalizedArticle(
        source=source,
        source_id=source_id,
        title=title,
        summary=summary,
        content=content,
        url=url,
        published_at=datetime(2026, 5, 10, 10, 0, 0),
        tags=tags or [],
        score=score,
        dedupe_key=f"{source}:{source_id}",
    )


def test_filter_articles_respects_strategy_levels() -> None:
    loose_only = _article(
        title="普通消息",
        summary="涉及住房改善",
        source_id="1",
        url="https://example.com/1",
    )
    strict_hit = _article(
        title="社区医保服务提升",
        tags=["民生"],
        summary="医保与公共服务同步优化",
        source_id="2",
        url="https://example.com/2",
    )

    articles = [loose_only, strict_hit]

    assert len(filter_articles(articles, strategy="loose")) == 2
    assert len(filter_articles(articles, strategy="standard")) >= 1
    assert filter_articles(articles, strategy="strict") == [strict_hit]


def test_deduplicate_articles_respects_strategy_levels() -> None:
    first = _article(
        title="民生政策解读",
        source="xinhua",
        source_id="dup-1",
        url="https://example.com/shared",
        score=90.0,
    )
    second = _article(
        title="民生政策解读",
        source="people_daily",
        source_id="dup-2",
        url="https://example.com/shared",
        score=85.0,
    )
    third = _article(
        title="民生政策解读",
        source="xinhua",
        source_id="dup-1",
        url="",
        score=88.0,
    )

    conservative = deduplicate_articles([first, second, third], strategy="conservative")
    standard = deduplicate_articles([first, second, third], strategy="standard")
    aggressive = deduplicate_articles([first, second, third], strategy="aggressive")

    assert len(conservative) >= len(standard)
    assert len(aggressive) <= len(standard)
