# Dashboard Stage Compare Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise the dashboard so the details area renders only one left-vs-right stage pair with right-side intersection semantics, and rebalance the summary area into a 2 x 2 layout.

**Architecture:** Keep the existing three-module page assembly and `result.stages` payload. Implement the revision inside the existing Jinja partials, using lightweight page-level helpers to derive the currently selected stage pair and its passed-item intersection. Keep preview A aligned in structure while allowing different visual styling.

**Tech Stack:** Python 3.13, Jinja2, standard library `http.server`, pytest, small inline JavaScript

---

## File Map

- Modify: `app/templates/_dashboard_summary.html.j2`
  - Rebuild the summary into four balanced cards: core metrics, stage conversion, run configuration, artifact entry.
- Modify: `app/templates/_dashboard_stage_details.html.j2`
  - Replace pre-rendered multi-pair DOM with a single current pair and render right-side items as the intersection of left and current stage data.
- Modify: `app/templates/dashboard.html.j2`
  - Adjust CSS for the new `2 x 2` summary and the simplified compare shell.
- Modify: `app/templates/_preview_a_summary.html.j2`
  - Mirror the same summary information structure in preview A.
- Modify: `app/templates/_preview_a_stage_details.html.j2`
  - Mirror the same single-pair compare semantics in preview A.
- Modify: `app/templates/dashboard_preview_a.html.j2`
  - Align preview A styling with the revised summary/detail semantics.
- Modify: `app/tests/test_dashboard.py`
  - Lock the new intersection semantics and revised summary structure.

---

### Task 1: Lock revised detail and summary semantics with failing tests

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_build_dashboard_html_stage_details_render_only_current_pair() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "standard",
            "time_strategies": ["source_day"],
            "dedupe_strategy": "standard",
            "raw_count": 3,
            "filtered_count": 2,
            "selected_count": 1,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [],
                "filtered_articles": [
                    {"title": "保留文章", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": 91.0, "tags": ["民生"], "published_at": "2026-05-10 08:00:00"},
                    {"title": "淘汰文章", "source": "xinhua", "url": "https://example.com/b", "summary": "摘要B", "score": 88.0, "tags": ["民生"], "published_at": "2026-05-10 08:10:00"},
                ],
                "deduped_articles": [
                    {"title": "保留文章", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": 91.0, "tags": ["民生"], "published_at": "2026-05-10 08:00:00"},
                ],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert html.count('data-stage-pair=') == 1
    assert "保留文章" in html
    assert "淘汰文章" in html
    assert "当前阶段通过数" in html
    assert "当前阶段淘汰数" in html


def test_build_dashboard_html_right_panel_shows_intersection_not_full_current_stage() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "standard",
            "time_strategies": ["source_day"],
            "dedupe_strategy": "standard",
            "raw_count": 4,
            "filtered_count": 2,
            "selected_count": 1,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [],
                "filtered_articles": [
                    {"title": "左栏命中", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": 91.0, "tags": [], "published_at": "2026-05-10 08:00:00"},
                ],
                "deduped_articles": [
                    {"title": "左栏命中", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": 91.0, "tags": [], "published_at": "2026-05-10 08:00:00"},
                    {"title": "不应单独出现", "source": "cctv", "url": "https://example.com/extra", "summary": "摘要X", "score": 93.0, "tags": [], "published_at": "2026-05-10 08:20:00"},
                ],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "左栏命中" in html
    assert "不应单独出现" not in html


def test_build_dashboard_html_summary_uses_four_balanced_sections() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["people_daily", "people_app", "cctv", "xinhua"],
            "filter_strategy": "strict",
            "time_strategies": ["source_day", "source_window"],
            "dedupe_strategy": "aggressive",
            "raw_count": 111,
            "filtered_count": 7,
            "selected_count": 7,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {"raw_articles": [], "filtered_articles": [], "deduped_articles": [], "chosen_articles": []},
        },
        error_message="",
    )

    assert "核心统计" in html
    assert "阶段转化" in html
    assert "运行配置" in html
    assert "产物入口" in html
    assert "people_daily" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_render_only_current_pair app/tests/test_dashboard.py::test_build_dashboard_html_right_panel_shows_intersection_not_full_current_stage app/tests/test_dashboard.py::test_build_dashboard_html_summary_uses_four_balanced_sections -v`

Expected: FAIL because the current implementation still pre-renders all stage pairs and uses the older `3 + 1` summary layout.

- [ ] **Step 3: Write minimal implementation**

```jinja2
{% set stage_pairs = {...} %}
{% set selected_stage = "deduped_articles" %}
{% set selected_pair = stage_pairs[selected_stage] %}
{% set previous_items = result.stages[selected_pair.previous_key] %}
{% set current_items = result.stages[selected_pair.current_key] %}
{% set current_urls = current_items | map(attribute="url") | list %}
{% set passed_items = [] %}
{% for article in previous_items %}
  {% if article.url in current_urls %}
    {% set _ = passed_items.append(article) %}
  {% endif %}
{% endfor %}
```

```jinja2
<div class="summary-grid summary-grid-balanced">
  <section class="summary-card">核心统计</section>
  <section class="summary-card">阶段转化</section>
  <section class="summary-card">运行配置</section>
  <section class="summary-card">产物入口</section>
</div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_render_only_current_pair app/tests/test_dashboard.py::test_build_dashboard_html_right_panel_shows_intersection_not_full_current_stage app/tests/test_dashboard.py::test_build_dashboard_html_summary_uses_four_balanced_sections -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/templates/_dashboard_summary.html.j2 app/templates/_dashboard_stage_details.html.j2
git commit -m "test: lock dashboard stage compare revision semantics"
```

### Task 2: Implement single-pair compare rendering for the formal dashboard

**Files:**
- Modify: `app/templates/_dashboard_stage_details.html.j2`
- Modify: `app/templates/dashboard.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_stage_details_report_passed_and_removed_counts() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "standard",
            "time_strategies": ["source_day"],
            "dedupe_strategy": "standard",
            "raw_count": 3,
            "filtered_count": 2,
            "selected_count": 1,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [],
                "filtered_articles": [
                    {"title": "文章 A", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": 91.0, "tags": [], "published_at": "2026-05-10 08:00:00"},
                    {"title": "文章 B", "source": "xinhua", "url": "https://example.com/b", "summary": "摘要B", "score": 88.0, "tags": [], "published_at": "2026-05-10 08:10:00"},
                ],
                "deduped_articles": [
                    {"title": "文章 A", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": 91.0, "tags": [], "published_at": "2026-05-10 08:00:00"},
                ],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "当前阶段通过数：1" in html
    assert "当前阶段淘汰数：1" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_report_passed_and_removed_counts -v`

Expected: FAIL because the current template does not expose the revised count copy.

- [ ] **Step 3: Write minimal implementation**

```jinja2
<div class="stage-panel-count">当前阶段通过数：{{ passed_items | length }}</div>
<div class="stage-panel-count">当前阶段淘汰数：{{ (previous_items | length) - (passed_items | length) }}</div>
```

```css
.stage-compare-track { display: block; }
.stage-compare-pair { display: grid; grid-template-columns: 1fr 1fr; }
.stage-status-rail { grid-template-columns: repeat(3, minmax(0, 1fr)); }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_report_passed_and_removed_counts -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_dashboard_stage_details.html.j2 app/templates/dashboard.html.j2 app/tests/test_dashboard.py
git commit -m "feat: render single current stage pair on dashboard"
```

### Task 3: Rebalance the formal summary into a 2 x 2 layout

**Files:**
- Modify: `app/templates/_dashboard_summary.html.j2`
- Modify: `app/templates/dashboard.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_summary_uses_badges_for_sources_and_split_cards() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["people_daily", "people_app", "cctv", "xinhua"],
            "filter_strategy": "strict",
            "time_strategies": ["source_day", "source_window"],
            "dedupe_strategy": "aggressive",
            "raw_count": 111,
            "filtered_count": 7,
            "selected_count": 7,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {"raw_articles": [], "filtered_articles": [], "deduped_articles": [], "chosen_articles": []},
        },
        error_message="",
    )

    assert 'class="summary-source-badges"' in html
    assert "原始 -> 过滤后" in html
    assert "过滤后 -> 最终入选" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_summary_uses_badges_for_sources_and_split_cards -v`

Expected: FAIL because the current summary does not have the revised grid or source badge wrapper.

- [ ] **Step 3: Write minimal implementation**

```jinja2
<div class="summary-grid summary-grid-balanced">
  <section class="summary-card summary-card-metrics">...</section>
  <section class="summary-card summary-card-conversion">...</section>
  <section class="summary-card summary-card-config">
    <div class="summary-source-badges">
      {% for source in result.selected_sources %}
      <span class="summary-source-badge">{{ source }}</span>
      {% endfor %}
    </div>
  </section>
  <section class="summary-card summary-card-artifacts">...</section>
</div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_summary_uses_badges_for_sources_and_split_cards -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_dashboard_summary.html.j2 app/templates/dashboard.html.j2 app/tests/test_dashboard.py
git commit -m "feat: rebalance dashboard summary layout"
```

### Task 4: Align preview A with the revised semantics

**Files:**
- Modify: `app/templates/_preview_a_summary.html.j2`
- Modify: `app/templates/_preview_a_stage_details.html.j2`
- Modify: `app/templates/dashboard_preview_a.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_preview_html_uses_single_pair_intersection_semantics() -> None:
    html = build_dashboard_preview_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "standard",
            "time_strategies": ["source_day"],
            "dedupe_strategy": "standard",
            "raw_count": 3,
            "filtered_count": 2,
            "selected_count": 1,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [],
                "filtered_articles": [
                    {"title": "文章 A", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": 91.0, "tags": [], "published_at": "2026-05-10 08:00:00"},
                    {"title": "文章 B", "source": "xinhua", "url": "https://example.com/b", "summary": "摘要B", "score": 88.0, "tags": [], "published_at": "2026-05-10 08:10:00"},
                ],
                "deduped_articles": [
                    {"title": "文章 A", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": 91.0, "tags": [], "published_at": "2026-05-10 08:00:00"},
                ],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert html.count('data-stage-pair=') == 1
    assert "当前阶段通过数" in html
    assert "核心统计" in html
    assert "产物入口" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_preview_html_uses_single_pair_intersection_semantics -v`

Expected: FAIL because preview A still follows the previous summary/detail contract.

- [ ] **Step 3: Write minimal implementation**

```jinja2
{# mirror the formal dashboard structure with preview-specific class names #}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_preview_html_uses_single_pair_intersection_semantics -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_preview_a_summary.html.j2 app/templates/_preview_a_stage_details.html.j2 app/templates/dashboard_preview_a.html.j2 app/tests/test_dashboard.py
git commit -m "feat: align preview dashboard with revised compare semantics"
```

### Task 5: Run focused verification and manual browser checks

**Files:**
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Run the focused suite**

Run: `pytest app/tests/test_dashboard.py -q`

Expected: PASS

- [ ] **Step 2: Start the dashboard locally**

Run: `python3 -c "from app.dashboard_server import serve_dashboard; serve_dashboard(port=8001)"`

Expected: stdout contains `dashboard=http://127.0.0.1:8001/`

- [ ] **Step 3: Verify the formal dashboard**

Open: `http://127.0.0.1:8001/`

Expected:
- summary renders as four balanced blocks
- current detail view shows only one left-vs-right pair
- right panel omits items that were never in the left panel
- default view remains `过滤后 -> 去重后`

- [ ] **Step 4: Verify preview A**

Open: `http://127.0.0.1:8001/preview/design-a`

Expected:
- preview keeps richer styling
- summary follows the same four-block structure
- details follow the same single-pair intersection semantics

- [ ] **Step 5: Commit**

```bash
git add app/templates/_dashboard_summary.html.j2 app/templates/_dashboard_stage_details.html.j2 app/templates/dashboard.html.j2 app/templates/_preview_a_summary.html.j2 app/templates/_preview_a_stage_details.html.j2 app/templates/dashboard_preview_a.html.j2 app/tests/test_dashboard.py
git commit -m "feat: implement dashboard stage compare revision"
```

---

## Self-Review

- Spec coverage:
  - Single current stage pair: covered by Task 1 and Task 2.
  - Right-side intersection semantics: covered by Task 1 and Task 2.
  - Summary `2 x 2` rebalance: covered by Task 1 and Task 3.
  - Preview alignment: covered by Task 4.
  - Manual verification: covered by Task 5.
- Placeholder scan:
  - No `TODO`, `TBD`, or deferred placeholders remain.
- Type consistency:
  - Stage keys consistently use `raw_articles`, `filtered_articles`, `deduped_articles`, and `chosen_articles`.
  - Default compare stage remains `deduped_articles`.
