from datetime import datetime

from app.models import NormalizedArticle
from app.pipeline.score import score_articles


def _article(title: str, summary: str, tags: list[str]) -> NormalizedArticle:
    return NormalizedArticle(
        source="people",
        source_id=title,
        title=title,
        url=f"https://example.com/{title}",
        published_at=datetime(2026, 5, 10, 21, 0, 0),
        summary=summary,
        content=summary,
        tags=tags,
    )


def test_score_articles_orders_by_minsheng_impact() -> None:
    articles = [
        _article("景区推出夜游活动", "文旅消费持续升温。", ["文旅"]),
        _article("多地提高养老金待遇", "养老保障政策进一步落地。", ["养老", "社保"]),
    ]

    scored = score_articles(articles)

    assert scored[0].title == "多地提高养老金待遇"
    assert scored[0].score > scored[1].score
    assert "topic:养老" in scored[0].reason_codes


def test_score_articles_adds_freshness_signal() -> None:
    article = _article("各地发放消费券", "带动假日消费，群众直接受益。", ["消费"])

    scored = score_articles([article])

    assert scored[0].score >= 70
    assert any(code.startswith("freshness:") for code in scored[0].reason_codes)
