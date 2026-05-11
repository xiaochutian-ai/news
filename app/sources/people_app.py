from __future__ import annotations

from datetime import datetime
import json

from bs4 import BeautifulSoup

from app.models import RawArticle
from app.sources.base import BaseSourceAdapter


PEOPLE_APP_BASE = "https://www.peopleapp.com"
PEOPLE_APP_HOME = f"{PEOPLE_APP_BASE}/"
NUXT_DATA_SCRIPT_ID = "__NUXT_DATA__"
PEOPLE_APP_CHANNEL_KEYS = ("hot", "ruiping")


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


def parse_people_app_nuxt_payload(payload_text: str, *, source_day_compact: str) -> list[RawArticle]:
    decoded = _decode_nuxt_payload(payload_text)
    data = decoded.get("data", {})
    if not isinstance(data, dict):
        return []

    target_day = datetime.strptime(source_day_compact, "%Y%m%d").date()
    articles: list[RawArticle] = []
    seen_urls: set[str] = set()

    for channel_key in PEOPLE_APP_CHANNEL_KEYS:
        channel = data.get(channel_key, {})
        if not isinstance(channel, dict):
            continue
        channel_data = channel.get("data", {})
        if not isinstance(channel_data, dict):
            continue
        items = channel_data.get("list", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            title = " ".join(str(item.get("newsTitle", "")).split())
            object_id = str(item.get("objectId", "")).strip()
            rel_id = item.get("relId")
            published_at = _parse_people_app_timestamp(item.get("createTime"))
            if not title or not object_id or rel_id in (None, "") or published_at is None:
                continue
            if published_at.date() != target_day:
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
                    metadata={"channel": channel_key},
                )
            )
    return articles


def parse_people_app_homepage(html: str, *, source_day_compact: str) -> list[RawArticle]:
    soup = BeautifulSoup(html, "html.parser")
    payload_node = soup.find("script", id=NUXT_DATA_SCRIPT_ID)
    payload_text = payload_node.string if payload_node else ""
    if not payload_text:
        return []
    return parse_people_app_nuxt_payload(payload_text, source_day_compact=source_day_compact)


class PeopleAppAdapter(BaseSourceAdapter):
    source_name = "people_app"
    home_url = PEOPLE_APP_HOME

    def fetch(self, source_day_compact: str) -> list[RawArticle]:
        html = self.get_text(self.home_url)
        candidates = parse_people_app_homepage(html, source_day_compact=source_day_compact)
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
