from __future__ import annotations

import re
from datetime import datetime

from app.models import NormalizedArticle, RawArticle


TOPIC_KEYWORDS = {
    "医保": "医保",
    "医疗": "医疗",
    "养老": "养老",
    "养老金": "养老",
    "就业": "就业",
    "住房": "住房",
    "小区": "住房",
    "消费": "消费",
    "婚姻登记": "公共服务",
    "全国通办": "公共服务",
    "教育": "教育",
    "社保": "社保",
    "文旅": "文旅",
    "生态": "生态",
}


def build_dedupe_key(article: RawArticle) -> str:
    normalized_title = re.sub(r"\s+", "", article.title).lower()
    normalized_url = article.url.rstrip("/").lower()
    return f"{article.source}:{article.source_id}:{normalized_title}:{normalized_url}"


def _infer_tags(article: RawArticle) -> list[str]:
    combined = f"{article.title} {article.summary} {article.content}"
    tags: list[str] = []
    for keyword, tag in TOPIC_KEYWORDS.items():
        if keyword in combined and tag not in tags:
            tags.append(tag)
    if not tags and "群众" in combined:
        tags.append("民生")
    return tags


def normalize_articles(raw_articles: list[RawArticle]) -> list[NormalizedArticle]:
    normalized: list[NormalizedArticle] = []
    for article in raw_articles:
        published_at = article.published_at or datetime.now()
        normalized.append(
            NormalizedArticle(
                source=article.source,
                source_id=article.source_id,
                title=article.title,
                url=article.url,
                published_at=published_at,
                summary=article.summary or article.title,
                content=article.content or article.summary or article.title,
                tags=_infer_tags(article),
                dedupe_key=build_dedupe_key(article),
            )
        )
    return normalized
