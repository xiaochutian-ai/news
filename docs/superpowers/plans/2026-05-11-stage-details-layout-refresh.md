# Stage Details Layout Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Dashboard stage-details area into a clearer stage-first workspace with better hierarchy and friendlier interaction.

**Architecture:** Keep the existing server-side stage payloads and stage-switch script, but redesign the template structure into a stepper header, a compact summary strip, a primary before/after comparison canvas, and collapsible secondary diff panels. Reuse the same data contract for both the standard and preview templates so interaction stays consistent.

**Tech Stack:** Jinja2 templates, inline CSS, vanilla JavaScript, `pytest`

---

### Task 1: Lock the New Layout Contract

**Files:**
- Modify: `/Users/bytedance/news/app/tests/test_dashboard.py`
- Test: `/Users/bytedance/news/app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_uses_stage_stepper_and_compact_summary_strip() -> None:
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

    assert "阶段摘要" in html
    assert "主视区" in html
    assert "次级差异" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_uses_stage_stepper_and_compact_summary_strip -q`
Expected: FAIL because the current template does not contain the new layout markers.

- [ ] **Step 3: Write minimal implementation**

```python
# Update the stage-details template so the rendered HTML includes:
# - "阶段摘要"
# - "主视区"
# - "次级差异"
# while preserving existing stage-switch data and handlers.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_uses_stage_stepper_and_compact_summary_strip -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/templates/_dashboard_stage_details.html.j2 app/templates/dashboard.html.j2
git commit -m "test: lock stage details layout contract"
```

### Task 2: Rebuild Standard Dashboard Stage Workspace

**Files:**
- Modify: `/Users/bytedance/news/app/templates/_dashboard_stage_details.html.j2`
- Modify: `/Users/bytedance/news/app/templates/dashboard.html.j2`
- Test: `/Users/bytedance/news/app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_stage_details_collapses_secondary_diffs() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result=sample_stage_result(),
        error_message="",
    )

    assert "删除条目（可展开）" in html
    assert "排序变化（可展开）" in html
    assert '<details class="stage-secondary-details"' in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_collapses_secondary_diffs -q`
Expected: FAIL because secondary diff panels are currently always expanded.

- [ ] **Step 3: Write minimal implementation**

```python
# Update the standard template/CSS to:
# - turn stage buttons into a compact horizontal stepper
# - add a thin summary strip for counts
# - keep the before/after comparison as the main canvas
# - move removed/rank-change lists into collapsible details sections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_details_collapses_secondary_diffs -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_dashboard_stage_details.html.j2 app/templates/dashboard.html.j2 app/tests/test_dashboard.py
git commit -m "feat: redesign standard stage details workspace"
```

### Task 3: Sync Preview Layout and Validate Interaction

**Files:**
- Modify: `/Users/bytedance/news/app/templates/_preview_a_stage_details.html.j2`
- Modify: `/Users/bytedance/news/app/templates/dashboard_preview_a.html.j2`
- Test: `/Users/bytedance/news/app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_preview_html_matches_stage_workspace_structure() -> None:
    html = build_dashboard_preview_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result=sample_stage_result(),
        error_message="",
    )

    assert "阶段摘要" in html
    assert "删除条目（可展开）" in html
    assert "排序变化（可展开）" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_preview_html_matches_stage_workspace_structure -q`
Expected: FAIL because preview layout still uses the old detail grouping.

- [ ] **Step 3: Write minimal implementation**

```python
# Mirror the same stepper + summary strip + primary canvas + collapsible secondary diff
# structure in the preview template and its dark-theme CSS.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_preview_html_matches_stage_workspace_structure -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_preview_a_stage_details.html.j2 app/templates/dashboard_preview_a.html.j2 app/tests/test_dashboard.py
git commit -m "feat: sync preview stage workspace layout"
```

### Task 4: Verify End-to-End Interaction and Redeploy

**Files:**
- Modify: `/Users/bytedance/news/app/tests/test_dashboard.py`
- Test: `/Users/bytedance/news/app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_stage_buttons_and_secondary_details_coexist() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result=sample_stage_result(),
        error_message="",
    )

    assert 'data-stage="raw_articles"' in html
    assert 'data-stage="filtered_articles"' in html
    assert 'data-stage="deduped_articles"' in html
    assert 'data-stage="chosen_articles"' in html
    assert html.count('class="stage-secondary-details"') >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_stage_buttons_and_secondary_details_coexist -q`
Expected: FAIL until both interaction hooks and new secondary detail containers are present together.

- [ ] **Step 3: Write minimal implementation**

```python
# Finalize markup/classes so stage switching still works after the layout refresh,
# then redeploy and verify in the browser by clicking all four stages.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py -q && pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/templates/_dashboard_stage_details.html.j2 app/templates/_preview_a_stage_details.html.j2 app/templates/dashboard.html.j2 app/templates/dashboard_preview_a.html.j2
git commit -m "feat: polish stage details interaction layout"
```
