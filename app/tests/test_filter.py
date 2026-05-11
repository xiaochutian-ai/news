from datetime import datetime

from app.models import NormalizedArticle
from app.pipeline.filter import filter_minsheng_articles


def _article(title: str, summary: str) -> NormalizedArticle:
    return NormalizedArticle(
        source="test",
        source_id=title,
        title=title,
        url=f"https://example.com/{title}",
        published_at=datetime(2026, 5, 10, 20, 0, 0),
        summary=summary,
        content=summary,
        tags=[],
    )


def test_filter_keeps_minsheng_relevant_articles() -> None:
    articles = [
        _article("多地优化医保报销政策", "国家医保局发布新举措，减轻群众就医负担。"),
        _article("国际会议举行", "会议讨论全球局势，没有直接民生影响。"),
    ]

    filtered = filter_minsheng_articles(articles)

    assert [item.title for item in filtered] == ["多地优化医保报销政策"]


def test_filter_keeps_policy_articles_with_clear_people_impact() -> None:
    article = _article("国务院部署城市更新行动", "围绕老旧小区改造、住房和公共服务改善提出措施。")

    filtered = filter_minsheng_articles([article])

    assert len(filtered) == 1


def test_filter_keeps_articles_with_public_service_tag() -> None:
    article = _article("各地办理“全国通办”68.2万件", "婚姻登记全国通办，减少群众异地办事成本。")
    article.tags = ["公共服务"]

    filtered = filter_minsheng_articles([article])

    assert len(filtered) == 1
