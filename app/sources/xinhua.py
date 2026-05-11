from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import re
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from app.models import RawArticle
from app.sources.base import BaseSourceAdapter


LINK_DATE_PATTERN = re.compile(r"/(20\d{2})-(\d{2})/(\d{2})/")
LINK_DATE_COMPACT_PATTERN = re.compile(r"/(20\d{2})(\d{2})(\d{2})/")
XINHUA_LINK_PATTERN = re.compile(r"https?://(?:www\.)?news\.cn/(politics|local)/(\d{8})/[^/]+/c\.html")


def _parse_published_at(link: str, published_raw: str) -> datetime | None:
    if published_raw.strip():
        return parsedate_to_datetime(published_raw).replace(tzinfo=None)
    match = LINK_DATE_PATTERN.search(link)
    if not match:
        match = LINK_DATE_COMPACT_PATTERN.search(link)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    return datetime(year, month, day, 21, 0, 0)


def parse_xinhua_rss(xml_text: str, *, source: str) -> list[RawArticle]:
    root = ET.fromstring(xml_text)
    items: list[RawArticle] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        description = item.findtext("description") or ""
        summary = BeautifulSoup(description, "html.parser").get_text(" ", strip=True) or title
        published_raw = item.findtext("pubDate") or ""
        published_at = _parse_published_at(link, published_raw)
        items.append(
            RawArticle(
                source="xinhua",
                source_id=link.rsplit("/", 1)[-1],
                title=title,
                url=link,
                published_at=published_at,
                summary=summary,
                content=summary,
                metadata={"feed": source},
            )
        )
    return items


def parse_xinhua_channel_page(html: str, *, source_day_compact: str | None = None) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    matches: list[tuple[str, str]] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        title = " ".join(link.get_text(" ", strip=True).split())
        href = link["href"].strip()
        if not title or href in seen:
            continue
        matched = XINHUA_LINK_PATTERN.match(href)
        if not matched:
            continue
        seen.add(href)
        matches.append((title, href))
    matches.sort(key=lambda item: _parse_published_at(item[1], "") or datetime.min, reverse=True)
    return matches


class XinhuaAdapter(BaseSourceAdapter):
    source_name = "xinhua"
    channel_urls = [
        "http://m.news.cn/index.htm",
    ]

    def fetch(self, source_day_compact: str) -> list[RawArticle]:
        results: list[RawArticle] = []
        seen: set[str] = set()
        for channel_url in self.channel_urls:
            try:
                html = self.get_text(channel_url)
            except Exception:
                continue
            for title, link in parse_xinhua_channel_page(html):
                if link in seen:
                    continue
                seen.add(link)
                try:
                    detail_html = self.get_text(link)
                    detail = BeautifulSoup(detail_html, "html.parser")
                    paragraphs = [
                        " ".join(node.get_text(" ", strip=True).split())
                        for node in detail.find_all("p")
                    ]
                    paragraphs = [text for text in paragraphs if text]
                    summary = paragraphs[0] if paragraphs else title
                    content = "\n".join(paragraphs[:3]) if paragraphs else title
                except Exception:
                    summary = title
                    content = title
                results.append(
                    RawArticle(
                        source="xinhua",
                        source_id=link.rstrip("/").split("/")[-2],
                        title=title,
                        url=link,
                        published_at=_parse_published_at(link, ""),
                        summary=summary,
                        content=content,
                        metadata={"channel": channel_url},
                    )
                )
        results.sort(key=lambda article: article.published_at or datetime.min, reverse=True)
        return results
