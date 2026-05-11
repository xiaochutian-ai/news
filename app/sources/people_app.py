from __future__ import annotations

from datetime import datetime
import json

from bs4 import BeautifulSoup

from app.models import RawArticle
from app.sources.base import BaseSourceAdapter


PEOPLE_APP_BASE = "https://www.peopleapp.com"
PEOPLE_APP_HOME = f"{PEOPLE_APP_BASE}/"
NUXT_DATA_SCRIPT_ID = "__NUXT_DATA__"
PEOPLE_APP_HOT_CHANNEL_KEY = "hot"


def _resolve_nuxt_value(payload: list[object], node: object, memo: dict[int, object]) -> object:
    if isinstance(node, bool) or node is None or isinstance(node, str):
        return node
    if isinstance(node, int):
        if node < 0 or node >= len(payload):
            return node
        if node in memo:
            return memo[node]
        target = payload[node]
        if isinstance(target, (str, int, float, bool)) or target is None:
            memo[node] = target
            return target
        if (
            isinstance(target, list)
            and len(target) == 2
            and isinstance(target[0], str)
            and target[0] in {"Reactive", "ShallowReactive", "Ref"}
        ):
            memo[node] = None
            value = _resolve_nuxt_value(payload, target[1], memo)
            memo[node] = value
            return value
        memo[node] = None
        value = _resolve_nuxt_value(payload, target, memo)
        memo[node] = value
        return value
    if isinstance(node, list):
        return [_resolve_nuxt_value(payload, item, memo) for item in node]
    if isinstance(node, dict):
        return {key: _resolve_nuxt_value(payload, value, memo) for key, value in node.items()}
    return node


def _decode_nuxt_payload(payload_text: str) -> dict[str, object]:
    payload = json.loads(payload_text)
    decoded = _resolve_nuxt_value(payload, 0, {})
    return decoded if isinstance(decoded, dict) else {}


def _build_people_app_url(object_id: str, rel_id: str | int) -> str:
    return f"{PEOPLE_APP_BASE}/column/{object_id}-{rel_id}"


def _parse_people_app_timestamp(value: str | int | None) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text.isdigit():
        return None
    if len(text) == 13:
        return datetime.fromtimestamp(int(text) / 1000)
    if len(text) == 10:
        return datetime.fromtimestamp(int(text))
    return None


def _iter_people_app_articles(node: object) -> list[dict[str, object]]:
    if isinstance(node, list):
        articles: list[dict[str, object]] = []
        for item in node:
            articles.extend(_iter_people_app_articles(item))
        return articles

    if not isinstance(node, dict):
        return []

    articles: list[dict[str, object]] = []
    if {
        "newsTitle",
        "objectId",
        "relId",
        "createTime",
    }.issubset(node):
        articles.append(node)

    for value in node.values():
        articles.extend(_iter_people_app_articles(value))
    return articles


def parse_people_app_nuxt_payload(payload_text: str, *, _source_day_compact: str | None = None) -> list[RawArticle]:
    del _source_day_compact
    decoded = _decode_nuxt_payload(payload_text)
    data = decoded.get("data", {})
    if not isinstance(data, dict):
        return []

    articles: list[RawArticle] = []
    seen_urls: set[str] = set()

    channel = data.get(PEOPLE_APP_HOT_CHANNEL_KEY, {})
    if not isinstance(channel, dict):
        return []

    channel_data = channel.get("data", {})
    if not isinstance(channel_data, dict):
        return []

    for item in _iter_people_app_articles(channel_data):
        title = " ".join(str(item.get("newsTitle", "")).split())
        object_id = str(item.get("objectId", "")).strip()
        rel_id = item.get("relId")
        published_at = _parse_people_app_timestamp(item.get("createTime"))
        if not title or not object_id or rel_id in (None, "") or published_at is None:
            continue
        url = _build_people_app_url(object_id, rel_id)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        summary = " ".join(str(item.get("newsTxt", "")).split()) or title
        articles.append(
            RawArticle(
                source="people_app",
                source_id=object_id,
                title=title,
                url=url,
                published_at=published_at,
                summary=summary,
                content=summary,
                metadata={"channel": PEOPLE_APP_HOT_CHANNEL_KEY},
            )
        )
    articles.sort(key=lambda article: article.published_at, reverse=True)
    return articles


def parse_people_app_homepage(html: str, *, _source_day_compact: str | None = None) -> list[RawArticle]:
    del _source_day_compact
    soup = BeautifulSoup(html, "html.parser")
    payload_node = soup.find("script", id=NUXT_DATA_SCRIPT_ID)
    payload_text = payload_node.string if payload_node else ""
    if not payload_text:
        return []
    return parse_people_app_nuxt_payload(payload_text)


class PeopleAppAdapter(BaseSourceAdapter):
    source_name = "people_app"
    home_url = PEOPLE_APP_HOME

    def fetch(self, _source_day_compact: str) -> list[RawArticle]:
        del _source_day_compact
        html = self.get_text(self.home_url)
        candidates = parse_people_app_homepage(html)
        enriched: list[RawArticle] = []
        for article in candidates:
            try:
                detail_html = self.get_text(article.url)
                soup = BeautifulSoup(detail_html, "html.parser")
                paragraphs = [
                    " ".join(node.get_text(" ", strip=True).split())
                    for node in soup.find_all("p")
                ]
                paragraphs = [text for text in paragraphs if text]
                article.summary = paragraphs[0] if paragraphs else article.summary or article.title
                article.content = "\n".join(paragraphs[:3]) if paragraphs else article.content or article.title
            except Exception:
                article.summary = article.summary or article.title
                article.content = article.content or article.title
            enriched.append(article)
        return enriched
