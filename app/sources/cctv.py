from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import json
from urllib.parse import urljoin
import re
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from app.models import RawArticle
from app.sources.base import BaseSourceAdapter


CCTV_LINK_PATTERN = re.compile(r"https://news\.cctv\.com/(\d{4})/(\d{2})/(\d{2})/[^/]+\.shtml")
JSONP_WRAPPER_PATTERN = re.compile(r"^[^(]+\((.*)\)\s*$", re.DOTALL)


def parse_cctv_rss(xml_text: str) -> list[RawArticle]:
    root = ET.fromstring(xml_text)
    items: list[RawArticle] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        published_at = parsedate_to_datetime(item.findtext("pubDate") or "").replace(tzinfo=None)
        summary = (item.findtext("description") or "").strip()
        items.append(
            RawArticle(
                source="cctv_rss",
                source_id=link.rsplit("/", 1)[-1],
                title=title,
                url=link,
                published_at=published_at,
                summary=summary,
                content=summary,
            )
        )
    return items


def parse_cctv_channel_page(html: str, *, source_day_compact: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    target_date = f"{source_day_compact[:4]}/{source_day_compact[4:6]}/{source_day_compact[6:]}"
    matches: list[tuple[str, str]] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        title = " ".join(link.get_text(" ", strip=True).split())
        href = link["href"].strip()
        if not title or href in seen:
            continue
        if not href.startswith("https://news.cctv.com/") or target_date not in href:
            continue
        if not CCTV_LINK_PATTERN.match(href):
            continue
        seen.add(href)
        matches.append((title, href))
    return matches


def parse_cctv_feed(feed_text: str, *, source_day_compact: str) -> list[tuple[str, str]]:
    matched = JSONP_WRAPPER_PATTERN.match(feed_text.strip())
    if not matched:
        return []
    payload = json.loads(matched.group(1))
    target_date = f"{source_day_compact[:4]}/{source_day_compact[4:6]}/{source_day_compact[6:]}"
    matches: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in payload.get("data", {}).get("list", []):
        title = " ".join(str(item.get("title", "")).split())
        url = str(item.get("url", "")).strip()
        if not title or not url or url in seen:
            continue
        if target_date not in url or not CCTV_LINK_PATTERN.match(url):
            continue
        seen.add(url)
        matches.append((title, url))
    return matches


class CCTVAdapter(BaseSourceAdapter):
    source_name = "cctv"
    feed_urls = [
        "https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/news_1.jsonp",
    ]

    def fetch(self, source_day_compact: str) -> list[RawArticle]:
        results: list[RawArticle] = []
        seen: set[str] = set()
        for feed_url in self.feed_urls:
            try:
                feed_text = self.get_text(feed_url, encoding="utf-8")
            except Exception:
                continue
            for title, absolute in parse_cctv_feed(feed_text, source_day_compact=source_day_compact):
                absolute = urljoin(feed_url, absolute)
                if absolute in seen:
                    continue
                seen.add(absolute)
                try:
                    detail_html = self.get_text(absolute)
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
                        source="cctv",
                        source_id=absolute.rsplit("/", 1)[-1],
                        title=title,
                        url=absolute,
                        published_at=datetime.fromisoformat(
                            f"{source_day_compact[:4]}-{source_day_compact[4:6]}-{source_day_compact[6:]}T21:30:00"
                        ),
                        summary=summary,
                        content=content,
                    )
                )
        return results
