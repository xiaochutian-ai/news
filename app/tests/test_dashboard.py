import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.dashboard_server import (
    DashboardHandler,
    build_artifact_url,
    build_dashboard_html,
    build_dashboard_preview_html,
    resolve_artifact_path,
)
from app.main import run_digest


def test_build_dashboard_html_shows_sources() -> None:
    html = build_dashboard_html(
        available_sources=[
            {"key": "people_daily", "label": "人民日报"},
            {"key": "cctv", "label": "央视"},
            {"key": "xinhua", "label": "新华社"},
        ],
        selected_sources=["people_daily", "xinhua"],
        result=None,
        error_message="",
    )

    assert "执行晨报生成" in html
    assert "新华社" in html
    assert 'name="sources"' in html


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


def test_build_dashboard_html_renders_stage_sections_and_artifact_links() -> None:
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
                "raw_articles": [
                    {
                        "title": "文章A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
                        "score": None,
                        "tags": [],
                        "published_at": "2026-05-10 10:00:00",
                    }
                ],
                "filtered_articles": [],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "原始候选明细" in html
    assert "过滤后明细" in html
    assert "去重后明细" in html
    assert "最终入选明细" in html
    assert "文章A" in html
    assert "/artifacts/output/drafts/a.html" in html
    assert "暂无数据" in html


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


def test_build_dashboard_html_uses_three_child_sections() -> None:
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

    assert html.count('class="panel"') == 3
    assert "生成选项" in html
    assert "结果摘要" in html
    assert "生成详情" in html


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

    assert "过滤策略：strict" in html
    assert "去重策略：aggressive" in html


def test_artifact_helpers_build_and_resolve_paths() -> None:
    artifact_path = Path("output/drafts/a.html")

    assert build_artifact_url(artifact_path) == "/artifacts/output/drafts/a.html"
    assert resolve_artifact_path("/artifacts/output/drafts/a.html") == artifact_path


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


def test_build_dashboard_preview_html_supports_grouped_and_collapsible_details() -> None:
    html = build_dashboard_preview_html(
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
                "raw_articles": [
                    {
                        "title": "文章A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
                        "score": 88.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 10:00:00",
                    }
                ],
                "filtered_articles": [],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "按来源分组" in html
    assert "<details" in html
    assert "xinhua" in html


def test_build_dashboard_preview_html_only_shows_top_three_per_group_before_secondary_expand() -> None:
    html = build_dashboard_preview_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        result={
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "raw_count": 4,
            "filtered_count": 4,
            "selected_count": 4,
            "html_path": "output/drafts/a.html",
            "json_path": "output/drafts/a.json",
            "html_url": "/artifacts/output/drafts/a.html",
            "json_url": "/artifacts/output/drafts/a.json",
            "stages": {
                "raw_articles": [
                    {"title": "文章1", "source": "xinhua", "url": "https://example.com/1", "summary": "摘要1", "score": 91.0, "tags": [], "published_at": "2026-05-10 10:00:00"},
                    {"title": "文章2", "source": "xinhua", "url": "https://example.com/2", "summary": "摘要2", "score": 90.0, "tags": [], "published_at": "2026-05-10 10:10:00"},
                    {"title": "文章3", "source": "xinhua", "url": "https://example.com/3", "summary": "摘要3", "score": 89.0, "tags": [], "published_at": "2026-05-10 10:20:00"},
                    {"title": "文章4", "source": "xinhua", "url": "https://example.com/4", "summary": "摘要4", "score": 88.0, "tags": [], "published_at": "2026-05-10 10:30:00"},
                ],
                "filtered_articles": [],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "展开剩余 1 条" in html
    assert "文章1" in html
    assert "文章2" in html
    assert "文章3" in html
    assert "文章4" in html


def test_dashboard_handler_posts_selected_strategies_to_run_digest() -> None:
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.path = "/run"
    body = b"sources=xinhua&filter_strategy=strict&dedupe_strategy=aggressive"
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.send_response = lambda code: None
    handler.send_header = lambda key, value: None
    handler.end_headers = lambda: None
    handler._write_html = lambda html: None

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


def test_run_digest_result_contains_selected_strategies() -> None:
    store = SimpleNamespace(
        is_seen=lambda dedupe_key, digest_date: False,
        save_draft=lambda draft, html_path, json_path: None,
        mark_seen=lambda chosen, digest_date: None,
        mark_publish_result=lambda digest_date, publish_mode, publish_status, publish_message: None,
    )

    with patch("app.main.StateStore", return_value=store), patch(
        "app.main.build_source_adapters", return_value=[]
    ), patch("app.main.normalize_articles", return_value=[]), patch(
        "app.main.filter_articles", return_value=[]
    ), patch("app.main.score_articles", return_value=[]), patch(
        "app.main.deduplicate_articles", return_value=[]
    ), patch("app.main.build_digest_draft") as mock_build_digest_draft, patch(
        "app.main.render_digest_html", return_value="<html></html>"
    ), patch("app.main.publish_digest", return_value=("skipped", "")):
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
