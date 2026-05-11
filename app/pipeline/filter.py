from __future__ import annotations

from app.models import NormalizedArticle

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


def filter_minsheng_articles(articles: list[NormalizedArticle]) -> list[NormalizedArticle]:
    filtered: list[NormalizedArticle] = []
    for article in articles:
        if any(tag in POSITIVE_TAGS for tag in article.tags):
            filtered.append(article)
            continue
        combined = f"{article.title} {article.summary} {article.content}"
        if any(keyword in combined for keyword in POSITIVE_KEYWORDS):
            filtered.append(article)
            continue
        if any(keyword in combined for keyword in NEGATIVE_KEYWORDS):
            continue
    return filtered
