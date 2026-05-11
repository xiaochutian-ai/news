# Xinhua Dashboard Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a selectable Xinhua source plus a minimal local dashboard web entrypoint that can run digest generation for chosen sources.

**Architecture:** Extend the existing adapter registry so source selection is explicit and testable, then wrap the current digest pipeline with a thin local dashboard server. Keep source fetching, digest generation, and HTML rendering in separate files so the new web layer stays small.

**Tech Stack:** Python 3.13, requests, BeautifulSoup, Jinja2, pytest, standard-library HTTP server

---

### Task 1: Add Xinhua Source Adapter

**Files:**
- Create: `app/sources/xinhua.py`
- Modify: `app/tests/test_sources.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime

from app.sources.xinhua import parse_xinhua_rss


def test_parse_xinhua_rss_extracts_articles() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title><![CDATA[提高青年求职能力 就业实训密集推出]]></title>
          <link>http://www.news.cn/local/2026-05/10/c_123456.htm</link>
          <pubDate>Sun, 10 May 2026 12:30:00 GMT</pubDate>
          <description><![CDATA[
            <a href="http://www.news.cn/local/2026-05/10/c_123456.htm">围绕就业创业推出新举措。</a>
          ]]></description>
        </item>
      </channel>
    </rss>
    """

    articles = parse_xinhua_rss(xml, source="xinhua_local")

    assert len(articles) == 1
    assert articles[0].source == "xinhua"
    assert articles[0].title == "提高青年求职能力 就业实训密集推出"
    assert articles[0].url == "http://www.news.cn/local/2026-05/10/c_123456.htm"
    assert articles[0].summary == "围绕就业创业推出新举措。"
    assert isinstance(articles[0].published_at, datetime)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_sources.py::test_parse_xinhua_rss_extracts_articles -v`
Expected: FAIL with `ModuleNotFoundError` or missing `parse_xinhua_rss`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from app.models import RawArticle
from app.sources.base import BaseSourceAdapter


def parse_xinhua_rss(xml_text: str, *, source: str) -> list[RawArticle]:
    root = ET.fromstring(xml_text)
    articles: list[RawArticle] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        summary_html = item.findtext("description") or ""
        summary = BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True)
        published_raw = item.findtext("pubDate") or ""
        published_at = parsedate_to_datetime(published_raw).replace(tzinfo=None)
        articles.append(
            RawArticle(
                source="xinhua",
                source_id=link.rsplit("/", 1)[-1],
                title=title,
                url=link,
                published_at=published_at,
                summary=summary or title,
                content=summary or title,
                metadata={"feed": source},
            )
        )
    return articles


class XinhuaAdapter(BaseSourceAdapter):
    source_name = "xinhua"
    rss_urls = [
        "http://www.xinhuanet.com/politics/news_politics.xml",
        "http://www.xinhuanet.com/local/news_province.xml",
    ]

    def fetch(self, source_day_compact: str) -> list[RawArticle]:
        source_day = f"{source_day_compact[:4]}-{source_day_compact[4:6]}-{source_day_compact[6:]}"
        collected: list[RawArticle] = []
        seen: set[str] = set()
        for rss_url in self.rss_urls:
            rss_text = self.get_text(rss_url)
            for article in parse_xinhua_rss(rss_text, source=rss_url):
                if source_day not in article.url or article.url in seen:
                    continue
                seen.add(article.url)
                collected.append(article)
        return collected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_sources.py::test_parse_xinhua_rss_extracts_articles -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/sources/xinhua.py app/tests/test_sources.py
git commit -m "feat: add xinhua source adapter"
```

### Task 2: Make Source Selection Explicit

**Files:**
- Modify: `app/sources/registry.py`
- Modify: `app/main.py`
- Test: `app/tests/test_sources.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.config import AppConfig
from app.sources.registry import build_source_adapters, list_available_sources


def test_build_source_adapters_uses_selected_sources() -> None:
    config = AppConfig()

    adapters = build_source_adapters(config, selected_sources=["people_daily", "xinhua"])

    assert [adapter.source_name for adapter in adapters] == ["people_daily", "xinhua"]


def test_list_available_sources_includes_xinhua() -> None:
    keys = [item["key"] for item in list_available_sources()]
    assert keys == ["people_daily", "cctv", "xinhua"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_sources.py -v`
Expected: FAIL because registry does not support explicit source selection

- [ ] **Step 3: Write minimal implementation**

```python
SOURCE_BUILDERS = {
    "people_daily": PeopleDailyAdapter,
    "cctv": CCTVAdapter,
    "xinhua": XinhuaAdapter,
}


def list_available_sources() -> list[dict[str, str]]:
    return [
        {"key": "people_daily", "label": "人民日报"},
        {"key": "cctv", "label": "央视"},
        {"key": "xinhua", "label": "新华社"},
    ]


def build_source_adapters(config: AppConfig, selected_sources: list[str] | None = None) -> list[object]:
    if selected_sources:
        return [SOURCE_BUILDERS[key]() for key in selected_sources if key in SOURCE_BUILDERS]

    adapters: list[object] = []
    if config.people_daily_enabled:
        adapters.append(PeopleDailyAdapter())
    if config.cctv_enabled:
        adapters.append(CCTVAdapter())
    return adapters
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_sources.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/sources/registry.py app/main.py app/tests/test_sources.py
git commit -m "feat: support explicit source selection"
```

### Task 3: Add Dashboard Web Skeleton

**Files:**
- Create: `app/dashboard_server.py`
- Create: `app/templates/dashboard.html.j2`
- Create: `app/tests/test_dashboard.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.dashboard_server import DashboardHandler, build_dashboard_html


def test_build_dashboard_html_shows_sources() -> None:
    html = build_dashboard_html(
        available_sources=[
            {"key": "people_daily", "label": "人民日报"},
            {"key": "cctv", "label": "央视"},
            {"key": "xinhua", "label": "新华社"},
        ],
        selected_sources=["people_daily", "xinhua"],
        result=None,
        error_message="",
    )

    assert "执行晨报生成" in html
    assert "新华社" in html
    assert "name=\"sources\"" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: FAIL with missing module or function

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import AppConfig
from app.main import run_digest
from app.sources.registry import list_available_sources


def build_dashboard_html(*, available_sources, selected_sources, result, error_message) -> str:
    env = Environment(
        loader=FileSystemLoader(Path("app/templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("dashboard.html.j2")
    return template.render(
        available_sources=available_sources,
        selected_sources=selected_sources,
        result=result,
        error_message=error_message,
    )


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        html = build_dashboard_html(
            available_sources=list_available_sources(),
            selected_sources=["people_daily", "cctv", "xinhua"],
            result=None,
            error_message="",
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(body)
        selected_sources = form.get("sources") or ["people_daily", "cctv", "xinhua"]
        result = run_digest(selected_sources=selected_sources)
        html = build_dashboard_html(
            available_sources=list_available_sources(),
            selected_sources=selected_sources,
            result=result,
            error_message="",
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def serve_dashboard(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"dashboard=http://{host}:{port}/")
    server.serve_forever()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/dashboard_server.py app/templates/dashboard.html.j2 app/tests/test_dashboard.py app/main.py
git commit -m "feat: add dashboard web skeleton"
```
