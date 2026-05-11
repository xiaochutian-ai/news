# Dashboard Stage Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show detailed article lists for each pipeline stage in the dashboard and provide in-page links to generated HTML/JSON artifacts.

**Architecture:** Extend `run_digest()` to serialize intermediate pipeline outputs into a dashboard-friendly `stages` payload. Keep the server thin by adding only a small artifact-serving route and render the new details entirely in the existing Jinja template.

**Tech Stack:** Python 3.13, Jinja2, http.server, pytest

---

### Task 1: Add failing dashboard rendering tests

**Files:**
- Modify: `app/tests/test_dashboard.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_build_dashboard_html_renders_stage_sections() -> None:
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
                "raw_articles": [{"title": "文章A", "source": "xinhua", "url": "https://example.com/a", "summary": "摘要A", "score": None, "tags": [], "published_at": "2026-05-10 10:00:00"}],
                "filtered_articles": [],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        },
        error_message="",
    )
    assert "原始候选明细" in html
    assert "文章A" in html
    assert "/artifacts/output/drafts/a.html" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: FAIL because the template does not render stage details or artifact routes yet

- [ ] **Step 3: Write minimal implementation**

```python
result["html_url"] = ...
result["stages"] = ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/tests/test_dashboard.py app/dashboard_server.py app/templates/dashboard.html.j2 app/main.py
git commit -m "test: cover dashboard stage details"
```

### Task 2: Serialize stage details in `run_digest`

**Files:**
- Modify: `app/main.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_digest_returns_stage_payload(monkeypatch, tmp_path) -> None:
    ...
    result = run_digest(selected_sources=["xinhua"])
    assert "stages" in result
    assert "raw_articles" in result["stages"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: FAIL because `run_digest()` does not expose serialized stage data

- [ ] **Step 3: Write minimal implementation**

```python
def _serialize_articles(items: list[...]) -> list[dict[str, object]]:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/tests/test_dashboard.py
git commit -m "feat: expose digest stage details"
```

### Task 3: Serve artifacts through dashboard routes

**Files:**
- Modify: `app/dashboard_server.py`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_dashboard_handler_serves_artifact_file(tmp_path) -> None:
    artifact = tmp_path / "artifact.html"
    artifact.write_text("<h1>ok</h1>", encoding="utf-8")
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: FAIL because `/artifacts/...` is not handled

- [ ] **Step 3: Write minimal implementation**

```python
if self.path.startswith("/artifacts/"):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/dashboard_server.py app/tests/test_dashboard.py
git commit -m "feat: serve dashboard artifacts"
```

### Task 4: Verify real dashboard flow

**Files:**
- Modify: `app/templates/dashboard.html.j2`
- Test: `app/tests/test_dashboard.py`

- [ ] **Step 1: Verify the real command**

```bash
python3 - <<'PY'
from app.main import run_digest
result = run_digest(selected_sources=['people_daily', 'cctv', 'xinhua'])
print(result['html_url'])
print(result['stages'].keys())
PY
```

- [ ] **Step 2: Run full test suite**

Run: `pytest app/tests -q`
Expected: PASS

- [ ] **Step 3: Restart dashboard**

```bash
python3 -c "from app.dashboard_server import serve_dashboard; serve_dashboard(port=8001)"
```

- [ ] **Step 4: Click through the page**

Open: `http://127.0.0.1:8001/`
Expected: stage detail sections render and artifact links open successfully

- [ ] **Step 5: Commit**

```bash
git add app/templates/dashboard.html.j2
git commit -m "feat: show stage details in dashboard"
```
