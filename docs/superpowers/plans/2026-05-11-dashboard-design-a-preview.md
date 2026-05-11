# Dashboard Design A Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-only dark "news command center" preview page at `/preview/design-a` without changing the current production dashboard template.

**Architecture:** Keep the existing dashboard route and templates unchanged. Add a separate preview template family plus preview GET/POST routes that reuse the same `run_digest()` result payload and artifact links.

**Tech Stack:** Python 3.13, Jinja2, pytest, Playwright

---

### Task 1: Lock the preview route and rendering contract

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_preview_html_renders_design_a_sections() -> None:
    html = build_dashboard_preview_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result=None,
        error_message="",
    )
    assert "晨报指挥台" in html
    assert "生成选项" in html
    assert "结果摘要" in html
    assert "生成详情" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_preview_html_renders_design_a_sections -v`
Expected: FAIL because no preview builder exists yet

- [ ] **Step 3: Write minimal implementation**

```python
def build_dashboard_preview_html(...):
    return _render_template("dashboard_preview_a.html.j2", ...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py::test_build_dashboard_preview_html_renders_design_a_sections -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/dashboard_server.py
git commit -m "test: lock design preview rendering"
```

### Task 2: Add the design preview templates

**Files:**
- Create: `app/templates/dashboard_preview_a.html.j2`
- Create: `app/templates/_preview_a_generation_options.html.j2`
- Create: `app/templates/_preview_a_summary.html.j2`
- Create: `app/templates/_preview_a_stage_details.html.j2`
- Modify: `app/dashboard_server.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_dashboard_preview_html_shows_dark_preview_copy() -> None:
    html = build_dashboard_preview_html(...)
    assert "深色新闻指挥舱" in html
    assert "情报总览" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: FAIL because the preview template files do not exist yet

- [ ] **Step 3: Write minimal implementation**

```jinja2
{% include "_preview_a_generation_options.html.j2" %}
{% include "_preview_a_summary.html.j2" %}
{% include "_preview_a_stage_details.html.j2" %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/templates/dashboard_preview_a.html.j2 app/templates/_preview_a_generation_options.html.j2 app/templates/_preview_a_summary.html.j2 app/templates/_preview_a_stage_details.html.j2 app/dashboard_server.py app/tests/test_dashboard.py
git commit -m "feat: add design a dashboard preview"
```

### Task 3: Wire the preview route and verify locally

**Files:**
- Modify: `app/dashboard_server.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Run the dashboard tests**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `pytest app/tests -q`
Expected: PASS

- [ ] **Step 3: Restart the server**

```bash
python3 -c "from app.dashboard_server import serve_dashboard; serve_dashboard(port=8001)"
```

- [ ] **Step 4: Open the preview page**

Open: `http://127.0.0.1:8001/preview/design-a`
Expected: dark preview loads and can run digest

- [ ] **Step 5: Commit**

```bash
git add app/dashboard_server.py app/templates/dashboard_preview_a.html.j2
git commit -m "feat: serve local design preview"
```
