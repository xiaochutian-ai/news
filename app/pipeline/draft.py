from __future__ import annotations

from datetime import datetime

from app.models import DigestDraft, DigestItem, NormalizedArticle


def build_digest_draft(
    articles: list[NormalizedArticle],
    digest_date: str,
    window_label: str,
    max_items: int = 7,
) -> DigestDraft:
    selected = sorted(articles, key=lambda item: item.score, reverse=True)[:max_items]
    items = [
        DigestItem(
            title=article.title,
            summary=article.summary or article.content[:120],
            source=article.source,
            url=article.url,
            published_at=article.published_at,
            score=article.score,
            reason=", ".join(article.reason_codes),
        )
        for article in selected
    ]
    intro = f"这是一版围绕群众衣食住行、医疗养老、就业消费等主题整理的晚间民生热点，共精选 {len(items)} 条。"
    return DigestDraft(
        digest_date=digest_date,
        title=f"{digest_date} 晨报",
        intro=intro,
        window_label=window_label,
        items=items,
        generated_at=datetime.now(),
    )
