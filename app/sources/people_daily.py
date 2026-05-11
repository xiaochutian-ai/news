from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.models import RawArticle
from app.sources.base import BaseSourceAdapter


PEOPLE_BASE = "https://data.people.com.cn"


def parse_people_daily_index(html: str, article_date: str) -> list[RawArticle]:
    compact = article_date.replace("-", "")
    soup = BeautifulSoup(html, "html.parser")
    items: list[RawArticle] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = " ".join(link.get_text(" ", strip=True).split())
        if not title or not href.startswith(f"/rmrb/{compact}/1/"):
            continue
        if href in seen:
            continue
        seen.add(href)
        items.append(
            RawArticle(
                source="people_daily",
                source_id=href.rsplit("/", 1)[-1],
                title=title,
                url=urljoin(PEOPLE_BASE, href),
                published_at=datetime.fromisoformat(f"{article_date}T21:00:00"),
            )
        )
    return items


class PeopleDailyAdapter(BaseSourceAdapter):
    source_name = "people_daily"

    def fetch(self, source_day_compact: str) -> list[RawArticle]:
        article_date = f"{source_day_compact[:4]}-{source_day_compact[4:6]}-{source_day_compact[6:]}"
        index_url = f"http://data.people.com.cn/rmrb/{source_day_compact}/1"
        html = self.get_text(index_url)
        candidates = parse_people_daily_index(html, article_date=article_date)
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
                article.summary = paragraphs[0] if paragraphs else article.title
                article.content = "\n".join(paragraphs[:3]) if paragraphs else article.title
            except Exception:
                article.summary = article.title
                article.content = article.title
            enriched.append(article)
        return enriched
