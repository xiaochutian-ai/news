from pathlib import Path

from app.dashboard_server import (
    build_artifact_url,
    build_dashboard_html,
    build_dashboard_preview_html,
    resolve_artifact_path,
)


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
