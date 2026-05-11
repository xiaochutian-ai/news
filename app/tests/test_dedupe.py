from datetime import datetime

from app.models import NormalizedArticle
from app.pipeline.dedupe import deduplicate_articles


def _article(source: str, title: str, url: str, score: float) -> NormalizedArticle:
    return NormalizedArticle(
        source=source,
        source_id=f"{source}-{title}",
        title=title,
        url=url,
        published_at=datetime(2026, 5, 10, 20, 0, 0),
        summary="summary",
        content="content",
        tags=[],
        score=score,
    )


def test_dedupe_prefers_higher_scored_article_for_same_title() -> None:
    articles = [
        _article("people", "消费品以旧换新继续扩围", "https://a.example/1", 82),
        _article("cctv", "消费品以旧换新继续扩围", "https://b.example/2", 90),
    ]

    deduped = deduplicate_articles(articles)

    assert len(deduped) == 1
    assert deduped[0].source == "cctv"


def test_dedupe_removes_articles_with_same_url() -> None:
    articles = [
        _article("people", "标题一", "https://same.example/item", 70),
        _article("people", "标题二", "https://same.example/item", 71),
    ]

    deduped = deduplicate_articles(articles)

    assert len(deduped) == 1
