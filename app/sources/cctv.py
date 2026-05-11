from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from app.models import RawArticle
from app.sources.base import BaseSourceAdapter


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


class CCTVAdapter(BaseSourceAdapter):
    source_name = "cctv"
    section_urls = [
        "https://news.cctv.com/china/",
        "https://news.cctv.com/society/",
    ]

    def fetch(self, source_day_compact: str) -> list[RawArticle]:
        date_prefix = (
            f"https://news.cctv.com/{source_day_compact[:4]}/"
            f"{source_day_compact[4:6]}/{source_day_compact[6:]}/"
        )
        results: list[RawArticle] = []
        seen: set[str] = set()
        for section_url in self.section_urls:
            try:
                html = self.get_text(section_url)
            except Exception:
                continue
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                title = " ".join(link.get_text(" ", strip=True).split())
                if not title:
                    continue
                absolute = urljoin(section_url, href)
                if not absolute.startswith(date_prefix) or absolute in seen:
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
