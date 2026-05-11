# Dashboard Generation Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the dashboard generation form so users can choose data sources, filter strategy, and dedupe strategy, and have those choices flow through the digest pipeline.

**Architecture:** Keep the existing dashboard routes and templates, and add two new fixed-strategy selects to both the formal dashboard and the design preview. Push behavior changes into `app/pipeline/filter.py` and `app/pipeline/dedupe.py` behind strategy-dispatch functions, while `app/main.py` and `app/dashboard_server.py` only pass parameters through and surface the selected values in the result payload.

**Tech Stack:** Python 3.13, Jinja2, pytest, standard library `http.server`

---

### Task 1: Lock the dashboard form contract with tests

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_shows_sources_and_strategy_fields() -> None:
    html = build_dashboard_html(
        available_sources=[
            {"key": "people_daily", "label": "人民日报"},
            {"key": "xinhua", "label": "新华社"},
        ],
        selected_sources=["people_daily"],
        result=None,
        error_message="",
    )

    assert 'name="sources"' in html
    assert 'name="filter_strategy"' in html
    assert 'name="dedupe_strategy"' in html
    assert 'value="standard"' in html
```

```python
def test_build_dashboard_preview_html_shows_sources_and_strategy_fields() -> None:
    html = build_dashboard_preview_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result=None,
        error_message="",
    )

    assert 'name="sources"' in html
    assert 'name="filter_strategy"' in html
    assert 'name="dedupe_strategy"' in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_shows_sources_and_strategy_fields app/tests/test_dashboard.py::test_build_dashboard_preview_html_shows_sources_and_strategy_fields -v`
Expected: FAIL because both templates currently render only the `sources` field

- [ ] **Step 3: Write minimal implementation**

```jinja2
<label>
  <span>过滤策略</span>
  <select name="filter_strategy">
    <option value="loose">宽松</option>
    <option value="standard" selected>标准</option>
    <option value="strict">严格</option>
  </select>
</label>

<label>
  <span>去重策略</span>
  <select name="dedupe_strategy">
    <option value="conservative">保守</option>
    <option value="standard" selected>标准</option>
    <option value="aggressive">激进</option>
  </select>
</label>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_shows_sources_and_strategy_fields app/tests/test_dashboard.py::test_build_dashboard_preview_html_shows_sources_and_strategy_fields -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/templates/_dashboard_generation_options.html.j2 app/templates/_preview_a_generation_options.html.j2
git commit -m "test: lock dashboard strategy fields"
```

### Task 2: Lock result summary strategy echo with tests

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Modify: `app/templates/_dashboard_summary.html.j2`
- Modify: `app/templates/_preview_a_summary.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_summary_shows_selected_strategies() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "strict",
            "dedupe_strategy": "aggressive",
            "raw_count": 2,
            "filtered_count": 1,
            "selected_count": 1,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [],
                "filtered_articles": [],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "过滤策略" in html
    assert "strict" in html
    assert "去重策略" in html
    assert "aggressive" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_summary_shows_selected_strategies -v`
Expected: FAIL because result summary does not render these fields yet

- [ ] **Step 3: Write minimal implementation**

```jinja2
<dl class="summary-meta">
  <div>
    <dt>过滤策略</dt>
    <dd>{{ result.filter_strategy or "standard" }}</dd>
  </div>
  <div>
    <dt>去重策略</dt>
    <dd>{{ result.dedupe_strategy or "standard" }}</dd>
  </div>
</dl>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_summary_shows_selected_strategies -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/templates/_dashboard_summary.html.j2 app/templates/_preview_a_summary.html.j2
git commit -m "feat: echo selected strategies in dashboard summary"
```

### Task 3: Add strategy behavior tests for filter and dedupe

**Files:**
- Create: `app/tests/test_pipeline_strategies.py`
- Test: `app/tests/test_pipeline_strategies.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime

from app.models import NormalizedArticle
from app.pipeline.dedupe import deduplicate_articles
from app.pipeline.filter import filter_articles


def _article(
    *,
    title: str,
    summary: str = "",
    content: str = "",
    tags: list[str] | None = None,
    source: str = "xinhua",
    url: str = "https://example.com/a",
    source_id: str = "a",
    score: float = 80.0,
) -> NormalizedArticle:
    return NormalizedArticle(
        source=source,
        source_id=source_id,
        title=title,
        summary=summary,
        content=content,
        url=url,
        published_at=datetime(2026, 5, 10, 10, 0, 0),
        tags=tags or [],
        score=score,
        dedupe_key=f"{source}:{source_id}",
    )


def test_filter_articles_respects_strategy_levels() -> None:
    loose_only = _article(title="普通消息", summary="涉及住房", source_id="1", url="https://example.com/1")
    strict_hit = _article(title="社区医保服务提升", tags=["民生"], summary="医保与公共服务同步优化", source_id="2", url="https://example.com/2")

    articles = [loose_only, strict_hit]

    assert len(filter_articles(articles, strategy="loose")) == 2
    assert len(filter_articles(articles, strategy="standard")) >= 1
    assert filter_articles(articles, strategy="strict") == [strict_hit]


def test_deduplicate_articles_respects_strategy_levels() -> None:
    first = _article(title="民生政策解读", source="xinhua", source_id="dup-1", url="https://example.com/shared", score=90.0)
    second = _article(title="民生政策解读", source="people_daily", source_id="dup-2", url="https://example.com/shared", score=85.0)
    third = _article(title="民生政策解读", source="xinhua", source_id="dup-1", url="", score=88.0)

    conservative = deduplicate_articles([first, second, third], strategy="conservative")
    standard = deduplicate_articles([first, second, third], strategy="standard")
    aggressive = deduplicate_articles([first, second, third], strategy="aggressive")

    assert len(conservative) >= len(standard)
    assert len(aggressive) <= len(standard)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_pipeline_strategies.py -v`
Expected: FAIL because `filter_articles()` does not exist yet and `deduplicate_articles()` has no `strategy` parameter

- [ ] **Step 3: Write minimal implementation**

```python
def filter_articles(
    articles: list[NormalizedArticle],
    strategy: str = "standard",
) -> list[NormalizedArticle]:
    if strategy == "loose":
        return _filter_loose_articles(articles)
    if strategy == "strict":
        return _filter_strict_articles(articles)
    return _filter_standard_articles(articles)
```

```python
def deduplicate_articles(
    articles: list[NormalizedArticle],
    strategy: str = "standard",
) -> list[NormalizedArticle]:
    if strategy == "conservative":
        return _deduplicate_conservative(articles)
    if strategy == "aggressive":
        return _deduplicate_aggressive(articles)
    return _deduplicate_standard(articles)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_pipeline_strategies.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_pipeline_strategies.py app/pipeline/filter.py app/pipeline/dedupe.py
git commit -m "feat: add dashboard-selectable pipeline strategies"
```

### Task 4: Wire selected strategies through dashboard routes and digest execution

**Files:**
- Modify: `app/main.py`
- Modify: `app/dashboard_server.py`
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch

from app.dashboard_server import DashboardHandler


def test_dashboard_handler_posts_selected_strategies_to_run_digest() -> None:
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.path = "/run"
    handler.headers = {"Content-Length": "68"}
    handler.rfile = io.BytesIO(
        b"sources=xinhua&filter_strategy=strict&dedupe_strategy=aggressive"
    )

    captured_html: list[str] = []
    handler._write_html = captured_html.append
    handler.send_response = lambda code: None
    handler.send_header = lambda key, value: None
    handler.end_headers = lambda: None
    handler.wfile = io.BytesIO()

    with patch("app.dashboard_server.run_digest") as mock_run_digest:
        mock_run_digest.return_value = {
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "strict",
            "dedupe_strategy": "aggressive",
            "raw_count": 0,
            "filtered_count": 0,
            "selected_count": 0,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [],
                "filtered_articles": [],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        }

        handler.do_POST()

    mock_run_digest.assert_called_once_with(
        selected_sources=["xinhua"],
        filter_strategy="strict",
        dedupe_strategy="aggressive",
    )
```

```python
def test_run_digest_result_contains_selected_strategies() -> None:
    with patch("app.main.build_source_adapters", return_value=[]), patch(
        "app.main.normalize_articles", return_value=[]
    ), patch("app.main.filter_articles", return_value=[]), patch(
        "app.main.score_articles", return_value=[]
    ), patch("app.main.deduplicate_articles", return_value=[]), patch(
        "app.main.build_digest_draft"
    ) as mock_build_digest_draft, patch("app.main.render_digest_html", return_value="<html></html>"), patch(
        "app.main.publish_digest", return_value=("skipped", ""))
    :
        mock_build_digest_draft.return_value = SimpleNamespace(
            digest_date="2026-05-11",
            html="",
        )

        result = run_digest(
            selected_sources=["xinhua"],
            filter_strategy="strict",
            dedupe_strategy="aggressive",
        )

    assert result["filter_strategy"] == "strict"
    assert result["dedupe_strategy"] == "aggressive"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_dashboard_handler_posts_selected_strategies_to_run_digest app/tests/test_dashboard.py::test_run_digest_result_contains_selected_strategies -v`
Expected: FAIL because POST parsing and `run_digest()` do not accept these parameters yet

- [ ] **Step 3: Write minimal implementation**

```python
def run_digest(
    digest_date: str | None = None,
    selected_sources: list[str] | None = None,
    filter_strategy: str = "standard",
    dedupe_strategy: str = "standard",
) -> dict[str, object]:
    config = AppConfig()
    config.ensure_directories()
    ctx = build_digest_context(date.fromisoformat(digest_date) if digest_date else None)
    store = StateStore(config.data_dir / "state.db", Path("app/storage/schema.sql"))

    raw_articles = []
    for adapter in build_source_adapters(config, selected_sources=selected_sources):
        raw_articles.extend(adapter.fetch(ctx["source_day_compact"]))

    normalized = normalize_articles(raw_articles)
    filtered = filter_articles(normalized, strategy=filter_strategy)
    scored = score_articles(filtered)
    deduped = deduplicate_articles(scored, strategy=dedupe_strategy)
    return {
        "selected_sources": selected_sources,
        "filter_strategy": filter_strategy,
        "dedupe_strategy": dedupe_strategy,
    }
```

```python
selected_sources = form.get("sources") or self.default_sources
filter_strategy = (form.get("filter_strategy") or ["standard"])[0]
dedupe_strategy = (form.get("dedupe_strategy") or ["standard"])[0]

result = run_digest(
    selected_sources=selected_sources,
    filter_strategy=filter_strategy,
    dedupe_strategy=dedupe_strategy,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_dashboard_handler_posts_selected_strategies_to_run_digest app/tests/test_dashboard.py::test_run_digest_result_contains_selected_strategies -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/dashboard_server.py app/tests/test_dashboard.py
git commit -m "feat: wire dashboard strategies through digest execution"
```

### Task 5: Run the focused suite and verify the real dashboard

**Files:**
- Modify: `README.md`
- Test: `app/tests/test_dashboard.py`
- Test: `app/tests/test_pipeline_strategies.py`

- [ ] **Step 1: Update the README usage**

```markdown
- 过滤策略：`宽松 / 标准 / 严格`
- 去重策略：`保守 / 标准 / 激进`
```

- [ ] **Step 2: Run the focused dashboard and pipeline suites**

Run: `pytest app/tests/test_dashboard.py app/tests/test_pipeline_strategies.py -q`
Expected: PASS

- [ ] **Step 3: Start the local dashboard**

Run: `./start_dashboard.sh`
Expected: output contains `dashboard=http://127.0.0.1:8000/`

- [ ] **Step 4: Validate the page manually**

Open: `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/preview/design-a`
Expected:
- both pages show `数据源 / 过滤策略 / 去重策略`
- changing the dropdowns and submitting shows the chosen strategies in the summary

- [ ] **Step 5: Commit**

```bash
git add README.md app/tests/test_dashboard.py app/tests/test_pipeline_strategies.py app/main.py app/dashboard_server.py app/pipeline/filter.py app/pipeline/dedupe.py app/templates/_dashboard_generation_options.html.j2 app/templates/_preview_a_generation_options.html.j2 app/templates/_dashboard_summary.html.j2 app/templates/_preview_a_summary.html.j2
git commit -m "feat: add dashboard generation strategies"
```
