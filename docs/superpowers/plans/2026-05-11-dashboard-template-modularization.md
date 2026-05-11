# Dashboard Template Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the dashboard detail area into a standalone template module and reshape the page into `生成选项 / 结果摘要 / 生成详情`.

**Architecture:** Keep the current Python view and result payload unchanged. Refactor only the Jinja template layer by moving the stage-detail rendering into a reusable partial and simplifying the main page template into three top-level sections.

**Tech Stack:** Python 3.13, Jinja2, pytest

---

### Task 1: Lock the new page structure with tests

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_uses_three_sections() -> None:
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
    assert "生成选项" in html
    assert "结果摘要" in html
    assert "生成详情" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_uses_three_sections -v`
Expected: FAIL because current template still uses `最近结果`

- [ ] **Step 3: Write minimal implementation**

```jinja2
<h2>生成选项</h2>
<h2>结果摘要</h2>
<h2>生成详情</h2>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_uses_three_sections -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/templates/dashboard.html.j2
git commit -m "test: lock dashboard section structure"
```

### Task 2: Extract the detail area into a template module

**Files:**
- Create: `app/templates/_dashboard_stage_details.html.j2`
- Modify: `app/templates/dashboard.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_still_renders_stage_details() -> None:
    ...
    assert "原始候选明细" in html
    assert "文章A" in html
```

- [ ] **Step 2: Run test to verify it fails if wiring breaks**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: FAIL if the new partial is missing or not included

- [ ] **Step 3: Write minimal implementation**

```jinja2
{% include "_dashboard_stage_details.html.j2" %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/dashboard.html.j2 app/templates/_dashboard_stage_details.html.j2 app/tests/test_dashboard.py
git commit -m "feat: extract dashboard detail template"
```

### Task 3: Verify no regression in real dashboard flow

**Files:**
- Modify: `app/templates/dashboard.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Run the dashboard test suite**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `pytest app/tests -q`
Expected: PASS

- [ ] **Step 3: Restart dashboard**

```bash
python3 -c "from app.dashboard_server import serve_dashboard; serve_dashboard(port=8001)"
```

- [ ] **Step 4: Validate the page manually**

Open: `http://127.0.0.1:8001/`
Expected: page shows `生成选项 / 结果摘要 / 生成详情`, and stage detail content still renders

- [ ] **Step 5: Commit**

```bash
git add app/templates/dashboard.html.j2 app/templates/_dashboard_stage_details.html.j2
git commit -m "refactor: modularize dashboard detail section"
```
