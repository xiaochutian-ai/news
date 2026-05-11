# People App Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `人民日报客户端` as a new independent source that runs alongside the existing `people_daily`, `cctv`, and `xinhua` adapters.

**Architecture:** Keep the existing source adapter abstraction intact and add one focused adapter file for `people_app`. Drive the work test-first: prove parsing and registration behavior in `app/tests/test_sources.py`, then wire configuration and Dashboard defaults, and finish with targeted verification.

**Tech Stack:** Python 3.13, requests, BeautifulSoup, pytest

---

### Task 1: Add failing tests for People App parsing and registration

**Files:**
- Modify: `app/tests/test_sources.py`
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_sources.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.sources.people_app import parse_people_app_list


def test_parse_people_app_list_extracts_current_day_articles() -> None:
    payload = """
    {"data":[
        {
            "title":"完善社区养老服务网络",
            "url":"https://www.peopleapp.com/article/1234567890",
            "publish_time":"2026-05-10 20:15:00"
        },
        {
            "title":"次日文章",
            "url":"https://www.peopleapp.com/article/9999999999",
            "publish_time":"2026-05-11 08:00:00"
        }
    ]}
    """
    articles = parse_people_app_list(payload, source_day_compact="20260510")
    assert len(articles) == 1
    assert articles[0] == (
        "完善社区养老服务网络",
        "https://www.peopleapp.com/article/1234567890",
        "2026-05-10 20:15:00",
    )


def test_build_source_adapters_supports_people_app() -> None:
    config = AppConfig()
    adapters = build_source_adapters(config, selected_sources=["people_daily", "people_app"])
    assert [adapter.source_name for adapter in adapters] == ["people_daily", "people_app"]


def test_list_available_sources_includes_people_app() -> None:
    keys = [item["key"] for item in list_available_sources()]
    assert keys == ["people_daily", "people_app", "cctv", "xinhua"]


def test_build_dashboard_html_shows_people_app_source() -> None:
    html = build_dashboard_html(
        available_sources=[
            {"key": "people_daily", "label": "人民日报"},
            {"key": "people_app", "label": "人民日报客户端"},
        ],
        selected_sources=["people_app"],
        result=None,
        error_message="",
    )
    assert "人民日报客户端" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_sources.py app/tests/test_dashboard.py -k "people_app or list_available_sources or build_source_adapters_supports_people_app or shows_people_app_source" -v`
Expected: FAIL with missing parser or missing source registration

- [ ] **Step 3: Write minimal implementation stubs**

```python
def parse_people_app_list(payload: str, *, source_day_compact: str) -> list[tuple[str, str, str]]:
    ...


class PeopleAppAdapter(BaseSourceAdapter):
    source_name = "people_app"
```

- [ ] **Step 4: Run the same tests to verify parser and registration pass**

Run: `pytest app/tests/test_sources.py app/tests/test_dashboard.py -k "people_app or list_available_sources or build_source_adapters_supports_people_app or shows_people_app_source" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_sources.py app/tests/test_dashboard.py app/sources/registry.py app/config.py app/dashboard_server.py app/sources/people_app.py
git commit -m "test: cover people app source registration"
```

### Task 2: Implement the People App adapter fetch flow

**Files:**
- Create: `app/sources/people_app.py`
- Modify: `app/tests/test_sources.py`
- Test: `app/tests/test_sources.py`

- [ ] **Step 1: Write the failing adapter test**

```python
def test_people_app_adapter_fetches_and_enriches_articles(monkeypatch) -> None:
    adapter = PeopleAppAdapter()
    list_payload = """
    {"data":[
        {
            "title":"推进便民服务升级",
            "url":"https://www.peopleapp.com/article/1234567890",
            "publish_time":"2026-05-10 20:15:00"
        }
    ]}
    """
    detail_html = "<html><body><p>政务服务进一步下沉。</p><p>群众办事更便捷。</p></body></html>"

    def fake_get_text(url: str, *, encoding: str | None = None) -> str:
        if url == adapter.feed_url:
            return list_payload
        return detail_html

    monkeypatch.setattr(adapter, "get_text", fake_get_text)
    articles = adapter.fetch("20260510")
    assert len(articles) == 1
    assert articles[0].source == "people_app"
    assert articles[0].summary == "政务服务进一步下沉。"
    assert articles[0].content == "政务服务进一步下沉。\n群众办事更便捷。"
```

- [ ] **Step 2: Run the adapter test to verify it fails**

Run: `pytest app/tests/test_sources.py::test_people_app_adapter_fetches_and_enriches_articles -v`
Expected: FAIL because `fetch()` is not implemented or returns no articles

- [ ] **Step 3: Write the minimal adapter implementation**

```python
class PeopleAppAdapter(BaseSourceAdapter):
    source_name = "people_app"
    feed_url = "https://www.peopleapp.com/"

    def fetch(self, source_day_compact: str) -> list[RawArticle]:
        ...
```

- [ ] **Step 4: Run the adapter-focused tests to verify they pass**

Run: `pytest app/tests/test_sources.py -k "people_app" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/sources/people_app.py app/tests/test_sources.py
git commit -m "feat: add people app source adapter"
```

### Task 3: Wire config and Dashboard defaults

**Files:**
- Modify: `app/config.py`
- Modify: `app/sources/registry.py`
- Modify: `app/dashboard_server.py`
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing default-source test**

```python
def test_dashboard_handler_default_sources_include_people_app() -> None:
    assert "people_app" in DashboardHandler.default_sources
```

- [ ] **Step 2: Run the Dashboard-focused tests to verify they fail**

Run: `pytest app/tests/test_dashboard.py -k "people_app or default_sources" -v`
Expected: FAIL because the default list does not include `people_app`

- [ ] **Step 3: Write the minimal wiring changes**

```python
people_app_enabled: bool = os.getenv("PEOPLE_APP_ENABLED", "true").lower() == "true"

SOURCE_BUILDERS = {
    "people_daily": PeopleDailyAdapter,
    "people_app": PeopleAppAdapter,
    "cctv": CCTVAdapter,
    "xinhua": XinhuaAdapter,
}

default_sources = ["people_daily", "people_app", "cctv", "xinhua"]
```

- [ ] **Step 4: Run the Dashboard-focused tests to verify they pass**

Run: `pytest app/tests/test_dashboard.py -k "people_app or default_sources" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/config.py app/sources/registry.py app/dashboard_server.py app/tests/test_dashboard.py
git commit -m "feat: expose people app source in dashboard"
```

### Task 4: Run targeted verification and full regression checks

**Files:**
- Test: `app/tests/test_sources.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Run source and Dashboard tests**

Run: `pytest app/tests/test_sources.py app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `pytest app/tests -q`
Expected: PASS

- [ ] **Step 3: Check diagnostics on edited files**

Run: `GetDiagnostics` for:
- `app/sources/people_app.py`
- `app/sources/registry.py`
- `app/config.py`
- `app/dashboard_server.py`
- `app/tests/test_sources.py`
- `app/tests/test_dashboard.py`

Expected: no new errors introduced

- [ ] **Step 4: Review the final diff**

```bash
git diff -- app/sources/people_app.py app/sources/registry.py app/config.py app/dashboard_server.py app/tests/test_sources.py app/tests/test_dashboard.py
```

- [ ] **Step 5: Commit**

```bash
git add app/sources/people_app.py app/sources/registry.py app/config.py app/dashboard_server.py app/tests/test_sources.py app/tests/test_dashboard.py
git commit -m "feat: add people app news source"
```
