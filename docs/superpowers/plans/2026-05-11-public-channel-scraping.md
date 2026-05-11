# Public Channel Scraping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken CCTV/Xinhua RSS-or-static assumptions with public channel page scraping that yields current-day candidates.

**Architecture:** Keep the existing adapter abstraction and swap only the source-specific fetch logic. Use test-first parsing helpers for public list pages, then feed current-day links into the same downstream normalization and filtering pipeline.

**Tech Stack:** Python 3.13, requests, BeautifulSoup, pytest

---

### Task 1: Add page parsing tests for CCTV and Xinhua

**Files:**
- Modify: `app/tests/test_sources.py`
- Test: `app/tests/test_sources.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_parse_cctv_channel_page_extracts_current_links() -> None:
    html = """
    <html><body>
      <a href="https://news.cctv.com/2026/05/10/ARTI123.shtml">社区食堂更方便了</a>
      <a href="https://news.cctv.com/2026/05/10/ARTI456.shtml">稳就业政策持续加力</a>
    </body></html>
    """
    links = parse_cctv_channel_page(html, source_day_compact="20260510")
    assert links == [
        ("社区食堂更方便了", "https://news.cctv.com/2026/05/10/ARTI123.shtml"),
        ("稳就业政策持续加力", "https://news.cctv.com/2026/05/10/ARTI456.shtml"),
    ]


def test_parse_xinhua_channel_page_extracts_current_links() -> None:
    html = """
    <html><body>
      <a href="https://www.news.cn/politics/20260510/abc123/c.html">养老服务再升级</a>
      <a href="https://www.news.cn/local/20260510/def456/c.html">社区卫生服务暖民心</a>
    </body></html>
    """
    links = parse_xinhua_channel_page(html, source_day_compact="20260510")
    assert links == [
        ("养老服务再升级", "https://www.news.cn/politics/20260510/abc123/c.html"),
        ("社区卫生服务暖民心", "https://www.news.cn/local/20260510/def456/c.html"),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_sources.py -v`
Expected: FAIL with missing parser functions

- [ ] **Step 3: Write minimal implementation**

```python
def parse_cctv_channel_page(html: str, *, source_day_compact: str) -> list[tuple[str, str]]:
    ...


def parse_xinhua_channel_page(html: str, *, source_day_compact: str) -> list[tuple[str, str]]:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_sources.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_sources.py app/sources/cctv.py app/sources/xinhua.py
git commit -m "test: cover public channel page parsing"
```

### Task 2: Switch CCTV adapter to public channel page scraping

**Files:**
- Modify: `app/sources/cctv.py`
- Test: `app/tests/test_sources.py`

- [ ] **Step 1: Write the failing test**

```python
def test_cctv_adapter_uses_channel_page_links(monkeypatch) -> None:
    adapter = CCTVAdapter()
    channel_html = '<a href="https://news.cctv.com/2026/05/10/ARTI123.shtml">社区食堂更方便了</a>'
    detail_html = "<html><body><p>社区食堂让老年人吃饭更方便。</p></body></html>"

    def fake_get_text(url: str, *, encoding: str | None = None) -> str:
        if url in adapter.section_urls:
            return channel_html
        return detail_html

    monkeypatch.setattr(adapter, "get_text", fake_get_text)
    articles = adapter.fetch("20260510")
    assert len(articles) == 1
    assert articles[0].summary == "社区食堂让老年人吃饭更方便。"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_sources.py::test_cctv_adapter_uses_channel_page_links -v`
Expected: FAIL because current adapter finds zero links

- [ ] **Step 3: Write minimal implementation**

```python
for title, absolute in parse_cctv_channel_page(html, source_day_compact=source_day_compact):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_sources.py::test_cctv_adapter_uses_channel_page_links -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/sources/cctv.py app/tests/test_sources.py
git commit -m "feat: scrape cctv public channel pages"
```

### Task 3: Switch Xinhua adapter to public channel page scraping

**Files:**
- Modify: `app/sources/xinhua.py`
- Test: `app/tests/test_sources.py`

- [ ] **Step 1: Write the failing test**

```python
def test_xinhua_adapter_uses_channel_page_links(monkeypatch) -> None:
    adapter = XinhuaAdapter()
    channel_html = '<a href="https://www.news.cn/local/20260510/def456/c.html">社区卫生服务暖民心</a>'
    detail_html = "<html><body><p>基层医疗服务进一步下沉。</p></body></html>"

    def fake_get_text(url: str, *, encoding: str | None = None) -> str:
        if url in adapter.channel_urls:
            return channel_html
        return detail_html

    monkeypatch.setattr(adapter, "get_text", fake_get_text)
    articles = adapter.fetch("20260510")
    assert len(articles) == 1
    assert articles[0].summary == "基层医疗服务进一步下沉。"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_sources.py::test_xinhua_adapter_uses_channel_page_links -v`
Expected: FAIL because current adapter still relies on RSS

- [ ] **Step 3: Write minimal implementation**

```python
for title, link in parse_xinhua_channel_page(html, source_day_compact=source_day_compact):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_sources.py::test_xinhua_adapter_uses_channel_page_links -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/sources/xinhua.py app/tests/test_sources.py
git commit -m "feat: scrape xinhua public channel pages"
```

### Task 4: Verify end-to-end source counts

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_dashboard_html_renders_latest_result_counts() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "raw_count": 2,
            "filtered_count": 1,
            "selected_count": 1,
            "html_path": "output/a.html",
            "json_path": "output/a.json",
        },
        error_message="",
    )
    assert "原始候选数" in html
    assert "2" in html
```

- [ ] **Step 2: Run test to verify it fails if needed**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS or fail only if rendering regressed during source updates

- [ ] **Step 3: Verify the real command**

```bash
python3 - <<'PY'
from app.main import run_digest
print(run_digest(selected_sources=['people_daily', 'cctv', 'xinhua']))
PY
```

- [ ] **Step 4: Run full test suite**

Run: `pytest app/tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py
git commit -m "test: verify public channel scraping flow"
```
