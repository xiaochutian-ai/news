# Dashboard Three-Part Assembly Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the dashboard template so the main template assembles exactly three child templates: `生成选项 / 结果摘要 / 生成详情`.

**Architecture:** Keep all Python-side rendering inputs unchanged and preserve the existing inline stylesheet in the main template. Move the option form and summary panel into standalone Jinja partials so the top-level template becomes a clear three-part assembler.

**Tech Stack:** Python 3.13, Jinja2, pytest

---

### Task 1: Lock the three-part assembly structure with tests

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_uses_three_child_sections() -> None:
    html = build_dashboard_html(...)
    assert html.count('class="panel"') == 3
    assert "生成选项" in html
    assert "结果摘要" in html
    assert "生成详情" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_uses_three_child_sections -v`
Expected: FAIL because the form and summary are still embedded in the main template

- [ ] **Step 3: Write minimal implementation**

```jinja2
{% include "_dashboard_generation_options.html.j2" %}
{% include "_dashboard_summary.html.j2" %}
{% include "_dashboard_stage_details.html.j2" %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_html_uses_three_child_sections -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/templates/dashboard.html.j2
git commit -m "test: lock dashboard three-part assembly"
```

### Task 2: Extract generation options and summary into child templates

**Files:**
- Create: `app/templates/_dashboard_generation_options.html.j2`
- Create: `app/templates/_dashboard_summary.html.j2`
- Modify: `app/templates/dashboard.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_html_still_renders_sources_and_artifact_links() -> None:
    html = build_dashboard_html(...)
    assert "执行晨报生成" in html
    assert "/artifacts/output/drafts/a.html" in html
```

- [ ] **Step 2: Run test to verify it fails if partial wiring breaks**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: FAIL if either partial is missing or not included

- [ ] **Step 3: Write minimal implementation**

```jinja2
<div class="panel">
  <h2>生成选项</h2>
  ...
</div>
```

```jinja2
<div class="panel">
  <h2>结果摘要</h2>
  ...
</div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/_dashboard_generation_options.html.j2 app/templates/_dashboard_summary.html.j2 app/templates/dashboard.html.j2 app/tests/test_dashboard.py
git commit -m "refactor: extract dashboard option and summary templates"
```

### Task 3: Verify real dashboard rendering

**Files:**
- Modify: `app/templates/dashboard.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Run the dashboard tests**

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
Expected: three panels render from child templates and the page still works end-to-end

- [ ] **Step 5: Commit**

```bash
git add app/templates/dashboard.html.j2 app/templates/_dashboard_generation_options.html.j2 app/templates/_dashboard_summary.html.j2
git commit -m "refactor: assemble dashboard from three partials"
```
