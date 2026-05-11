# Dashboard Stage Compare Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the dashboard into a structured three-module control surface, with a denser stage-details area that defaults to comparing `过滤后` versus `去重后`.

**Architecture:** Keep the existing three-template assembly and existing `run_digest()` result payload. Implement the redesign mostly in Jinja partials and page-level CSS, and use a tiny client-side stage toggle in the details module so we do not need to introduce new backend entities or route state.

**Tech Stack:** Python 3.13, Jinja2, standard library `http.server`, pytest, small inline JavaScript

---

## File Map

- Modify: `app/templates/dashboard.html.j2`
  - Refresh the formal dashboard page-level CSS so the three existing modules can render as a structured control console.
- Modify: `app/templates/dashboard_preview_a.html.j2`
  - Keep the preview page visually richer, but align its structure and detail interaction with the formal dashboard.
- Modify: `app/templates/_dashboard_generation_options.html.j2`
  - Reorganize the form into source, filter/dedupe, and time/action sections.
- Modify: `app/templates/_dashboard_summary.html.j2`
  - Keep summary independent, but compress it to metrics and execution metadata only.
- Modify: `app/templates/_dashboard_stage_details.html.j2`
  - Replace four flat stage cards with a status rail and a two-panel compare view using collapsible summaries.
- Modify: `app/templates/_preview_a_generation_options.html.j2`
  - Mirror the same semantics in the preview design.
- Modify: `app/templates/_preview_a_summary.html.j2`
  - Mirror the summary structure in the preview design.
- Modify: `app/templates/_preview_a_stage_details.html.j2`
  - Mirror the same stage-compare interaction in the preview design.
- Modify: `app/tests/test_dashboard.py`
  - Lock the new structure, default compare stage, and collapsible detail behavior.

---

### Task 1: Lock the redesigned rendering contract with failing tests

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_build_dashboard_html_generation_options_are_grouped_by_control_domain() -> None:
    html = build_dashboard_html(
        available_sources=[
            {"key": "people_daily", "label": "人民日报"},
            {"key": "xinhua", "label": "新华社"},
        ],
        selected_sources=["xinhua"],
        result=None,
        error_message="",
    )

    assert "信息源" in html
    assert "过滤策略" in html
    assert "时间筛选" in html
    assert "去重策略" in html
    assert "执行晨报生成" in html


def test_build_dashboard_html_defaults_to_filtered_vs_deduped_compare() -> None:
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
            "filtered_count": 3,
            "selected_count": 2,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [],
                "filtered_articles": [
                    {
                        "title": "过滤后文章",
                        "source": "xinhua",
                        "url": "https://example.com/f",
                        "summary": "过滤后摘要",
                        "score": 90.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 10:00:00",
                    }
                ],
                "deduped_articles": [
                    {
                        "title": "去重后文章",
                        "source": "xinhua",
                        "url": "https://example.com/d",
                        "summary": "去重后摘要",
                        "score": 92.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 10:05:00",
                    }
                ],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "过滤后" in html
    assert "去重后" in html
    assert 'data-default-stage="deduped_articles"' in html
    assert "<details" in html
    assert "展开摘要" in html


def test_build_dashboard_preview_html_uses_same_stage_compare_semantics() -> None:
    html = build_dashboard_preview_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result=None,
        error_message="",
    )

    assert "生成选项" in html
    assert "结果摘要" in html
    assert "生成详情" in html
    assert "信息源" in html
    assert "时间筛选" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_generation_options_are_grouped_by_control_domain app/tests/test_dashboard.py::test_build_dashboard_html_defaults_to_filtered_vs_deduped_compare app/tests/test_dashboard.py::test_build_dashboard_preview_html_uses_same_stage_compare_semantics -v`

Expected: FAIL because the current templates still render the loose form layout and flat stage cards.

- [ ] **Step 3: Write minimal implementation**

```jinja2
<section class="control-group">
  <div class="control-group-title">信息源</div>
  ...
</section>

<div class="stage-compare-shell" data-default-stage="deduped_articles">
  ...
  <details class="article-summary-toggle">
    <summary>展开摘要</summary>
    <div class="article-summary">{{ article.summary }}</div>
  </details>
</div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_generation_options_are_grouped_by_control_domain app/tests/test_dashboard.py::test_build_dashboard_html_defaults_to_filtered_vs_deduped_compare app/tests/test_dashboard.py::test_build_dashboard_preview_html_uses_same_stage_compare_semantics -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/templates/_dashboard_generation_options.html.j2 app/templates/_dashboard_stage_details.html.j2 app/templates/_preview_a_generation_options.html.j2 app/templates/_preview_a_stage_details.html.j2
git commit -m "test: lock dashboard stage compare redesign contract"
```

### Task 2: Rebuild the generation-options and summary modules around structured domains

**Files:**
- Modify: `app/templates/_dashboard_generation_options.html.j2`
- Modify: `app/templates/_dashboard_summary.html.j2`
- Modify: `app/templates/_preview_a_generation_options.html.j2`
- Modify: `app/templates/_preview_a_summary.html.j2`
- Modify: `app/templates/dashboard.html.j2`
- Modify: `app/templates/dashboard_preview_a.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_summary_keeps_only_metrics_and_run_metadata() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "strict",
            "time_strategies": ["source_day", "source_window"],
            "dedupe_strategy": "aggressive",
            "raw_count": 6,
            "filtered_count": 3,
            "selected_count": 2,
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

    assert "原始候选数" in html or "原始候选" in html
    assert "过滤策略" in html
    assert "时间策略" in html
    assert "去重策略" in html
    assert "/artifacts/output/drafts/a.html" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_summary_keeps_only_metrics_and_run_metadata -v`

Expected: FAIL because the current summary copy and structure are still the earlier flat layout.

- [ ] **Step 3: Write minimal implementation**

```jinja2
<div class="summary-grid">
  <div class="stats">
    <div class="stat">
      <div class="label">原始候选数</div>
      <div class="value">{{ result.raw_count }}</div>
    </div>
    ...
  </div>
  <div class="summary-meta-grid">
    <div class="summary-meta-item">
      <div class="summary-meta-label">过滤策略</div>
      <div class="summary-meta-value">{{ result.filter_strategy | default("standard") }}</div>
    </div>
    ...
  </div>
</div>
```

```css
.control-layout { display: grid; grid-template-columns: 1.2fr 1fr 0.9fr; gap: 16px; }
.control-group { border-radius: 16px; padding: 16px; }
.summary-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_summary_keeps_only_metrics_and_run_metadata -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_dashboard_generation_options.html.j2 app/templates/_dashboard_summary.html.j2 app/templates/_preview_a_generation_options.html.j2 app/templates/_preview_a_summary.html.j2 app/templates/dashboard.html.j2 app/templates/dashboard_preview_a.html.j2 app/tests/test_dashboard.py
git commit -m "feat: restructure dashboard controls and summary modules"
```

### Task 3: Replace flat stage cards with a status-first compare shell

**Files:**
- Modify: `app/templates/_dashboard_stage_details.html.j2`
- Modify: `app/templates/_preview_a_stage_details.html.j2`
- Modify: `app/templates/dashboard.html.j2`
- Modify: `app/templates/dashboard_preview_a.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_stage_details_render_status_rail_and_two_panels() -> None:
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
                    {
                        "title": "文章 A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要 A",
                        "score": 91.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 08:00:00",
                    }
                ],
                "deduped_articles": [
                    {
                        "title": "文章 A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要 A",
                        "score": 91.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 08:00:00",
                    }
                ],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "stage-status-rail" in html
    assert "stage-compare-panel" in html
    assert "过滤后" in html
    assert "去重后" in html
    assert "文章 A" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_render_status_rail_and_two_panels -v`

Expected: FAIL because the current details module still renders four independent stage cards.

- [ ] **Step 3: Write minimal implementation**

```jinja2
{% set stage_pairs = {
  "filtered_articles": {"previous": "raw_articles", "current": "filtered_articles", "previous_label": "原始候选", "current_label": "过滤后"},
  "deduped_articles": {"previous": "filtered_articles", "current": "deduped_articles", "previous_label": "过滤后", "current_label": "去重后"},
  "chosen_articles": {"previous": "deduped_articles", "current": "chosen_articles", "previous_label": "去重后", "current_label": "最终入选"},
} %}
{% set selected_stage = "deduped_articles" %}
{% set selected_pair = stage_pairs[selected_stage] %}

<div class="stage-compare-shell" data-default-stage="deduped_articles">
  <div class="stage-status-rail">
    <button type="button" class="stage-status-button is-active" data-stage="deduped_articles">去重后</button>
    ...
  </div>
  <div class="stage-compare-panels">
    <section class="stage-compare-panel" data-role="previous">...</section>
    <section class="stage-compare-panel" data-role="current">...</section>
  </div>
</div>
```

```css
.stage-shell { display: grid; grid-template-columns: 220px 1fr; gap: 16px; }
.stage-status-rail { display: grid; gap: 8px; }
.stage-status-button.is-active { border-color: rgba(99, 199, 255, 0.5); }
.stage-compare-panels { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.article-item { font-size: 12px; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_render_status_rail_and_two_panels -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_dashboard_stage_details.html.j2 app/templates/_preview_a_stage_details.html.j2 app/templates/dashboard.html.j2 app/templates/dashboard_preview_a.html.j2 app/tests/test_dashboard.py
git commit -m "feat: redesign dashboard stage details as compare panels"
```

### Task 4: Add minimal client-side stage switching and collapsible summaries

**Files:**
- Modify: `app/templates/_dashboard_stage_details.html.j2`
- Modify: `app/templates/_preview_a_stage_details.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_stage_details_include_toggle_script_and_collapsible_summary() -> None:
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
            "raw_count": 2,
            "filtered_count": 2,
            "selected_count": 1,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [],
                "filtered_articles": [
                    {
                        "title": "文章 A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要 A",
                        "score": 91.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 08:00:00",
                    }
                ],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "function switchStageCompare" in html
    assert 'data-stage="chosen_articles"' in html
    assert "<details" in html
    assert "展开摘要" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_include_toggle_script_and_collapsible_summary -v`

Expected: FAIL because the current details template has neither a stage toggle script nor the new compact summary toggle wording.

- [ ] **Step 3: Write minimal implementation**

```html
<script>
function switchStageCompare(container, stageKey) {
  const buttons = container.querySelectorAll("[data-stage]");
  const panels = container.querySelectorAll("[data-stage-pair]");
  buttons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.stage === stageKey);
  });
  panels.forEach((panel) => {
    panel.hidden = panel.dataset.stagePair !== stageKey;
  });
}

document.querySelectorAll(".stage-compare-shell").forEach((container) => {
  const defaultStage = container.dataset.defaultStage || "deduped_articles";
  switchStageCompare(container, defaultStage);
});
</script>
```

```jinja2
<details class="article-summary-toggle">
  <summary>展开摘要</summary>
  <div class="article-summary-body">{{ article.summary }}</div>
</details>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_include_toggle_script_and_collapsible_summary -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_dashboard_stage_details.html.j2 app/templates/_preview_a_stage_details.html.j2 app/tests/test_dashboard.py
git commit -m "feat: add lightweight dashboard stage switching"
```

### Task 5: Run the focused suite and verify both dashboard surfaces manually

**Files:**
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Run the focused suite**

Run: `pytest app/tests/test_dashboard.py -q`

Expected: PASS

- [ ] **Step 2: Start the dashboard locally**

Run: `python3 -m app.dashboard_server`

Expected: stdout contains `dashboard=http://127.0.0.1:8000/`

- [ ] **Step 3: Verify the formal dashboard**

Open: `http://127.0.0.1:8000/`

Expected:
- the page still renders exactly three modules
- `生成选项` shows grouped blocks for `信息源` / `过滤策略` / `时间筛选` / `去重策略`
- `结果摘要` remains separate from article details
- `生成详情` defaults to `过滤后 vs 去重后`
- summary text stays collapsed until expanded

- [ ] **Step 4: Verify the preview dashboard**

Open: `http://127.0.0.1:8000/preview/design-a`

Expected:
- preview keeps the richer visual styling
- preview uses the same grouped controls and compare semantics
- clicking `最终入选` changes the right-side comparison to `去重后 vs 最终入选`

- [ ] **Step 5: Commit**

```bash
git add app/templates/dashboard.html.j2 app/templates/dashboard_preview_a.html.j2 app/templates/_dashboard_generation_options.html.j2 app/templates/_dashboard_summary.html.j2 app/templates/_dashboard_stage_details.html.j2 app/templates/_preview_a_generation_options.html.j2 app/templates/_preview_a_summary.html.j2 app/templates/_preview_a_stage_details.html.j2 app/tests/test_dashboard.py
git commit -m "feat: redesign dashboard stage comparison layout"
```

---

## Self-Review

- Spec coverage:
  - `生成选项` 结构化分仓: covered by Task 1 and Task 2.
  - `结果摘要` 独立且只保留决策信息: covered by Task 2.
  - `生成详情` 默认 `过滤后 vs 去重后`: covered by Task 1 and Task 3.
  - `状态优先` 阶段条: covered by Task 3.
  - 摘要默认折叠: covered by Task 1 and Task 4.
  - 正式页与 preview A 语义一致: covered by Task 1, Task 2, Task 3, and Task 5.
- Placeholder scan:
  - No `TODO`, `TBD`, or “implement later” language remains.
  - Each code-changing step includes a concrete code sketch or exact command.
- Type and naming consistency:
  - Stage keys consistently use `raw_articles`, `filtered_articles`, `deduped_articles`, and `chosen_articles`.
  - Default compare stage consistently uses `deduped_articles`.

