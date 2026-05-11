from __future__ import annotations

from app.models import NormalizedArticle

TOPIC_WEIGHTS = {
    "养老": 28,
    "社保": 24,
    "医保": 24,
    "医疗": 24,
    "就业": 22,
    "住房": 22,
    "消费": 18,
    "文旅": 12,
    "民生": 20,
    "公共服务": 18,
}


def score_articles(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    scored: list[NormalizedArticle] = []
    for article in articles:
        score = 50.0
        reason_codes: list[str] = []
        for tag in article.tags:
            weight = TOPIC_WEIGHTS.get(tag, 0)
            if weight:
                score += weight
                reason_codes.append(f"topic:{tag}")
        score += 8
        reason_codes.append("freshness:recent")
        article.score = score
        article.reason_codes = reason_codes
        scored.append(article)
    return sorted(scored, key=lambda item: item.score, reverse=True)
