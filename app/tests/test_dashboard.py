import io
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.dashboard_server import (
    DashboardHandler,
    _build_stage_compare_payload,
    build_artifact_url,
    build_dashboard_html,
    build_dashboard_preview_html,
    resolve_artifact_path,
)
from app.main import run_digest


class _StageCompareDataPlacementParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, str]] = []
        self.stage_data_inside_shell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        class_attr = attrs_dict.get("class", "") or ""
        self.stack.append((tag, class_attr))
        if (
            tag == "script"
            and "stage-compare-data" in class_attr
            and any(parent_tag == "div" and "stage-compare-shell" in parent_class for parent_tag, parent_class in self.stack[:-1])
        ):
            self.stage_data_inside_shell = True

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index]
                break


def test_build_dashboard_html_shows_sources() -> None:
    html = build_dashboard_html(
        available_sources=[
            {"key": "people_daily", "label": "人民日报"},
            {"key": "people_app", "label": "人民日报客户端"},
            {"key": "cctv", "label": "央视"},
            {"key": "xinhua", "label": "新华社"},
        ],
        selected_sources=["people_daily", "xinhua"],
        result=None,
        error_message="",
    )

    assert "执行晨报生成" in html
    assert "新华社" in html
    assert "人民日报客户端" in html
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
    assert 'name="blocked_keywords"' in html
    assert 'name="time_strategy"' in html
    assert 'name="dedupe_strategy"' in html
    assert 'value="standard"' in html
    assert "习近平" in html


def test_build_dashboard_html_respects_explicit_empty_blocked_keywords() -> None:
    html = build_dashboard_html(
        available_sources=[{"key": "xinhua", "label": "新华社"}],
        selected_sources=["xinhua"],
        selected_blocked_keywords_text="",
        result=None,
        error_message="",
    )

    assert '<textarea name="blocked_keywords" rows="3" placeholder="用逗号、顿号或换行分隔"></textarea>' in html


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

    assert "阶段选择" in html
    assert "获取" in html
    assert "过滤" in html
    assert "去重" in html
    assert "入选" in html
    assert "文章A" in html
    assert "/artifacts/output/drafts/a.html" in html
    assert "当前阶段之后没有保留下来的数据。" in html


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


def test_build_dashboard_html_defaults_to_filtered_stage_compare() -> None:
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
    assert 'data-default-stage="filtered_articles"' in html
    assert "<details" in html
    assert "展开摘要" in html


def test_build_dashboard_html_stage_details_render_stage_selector_and_compare_workspace() -> None:
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
                        "title": "保留文章",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
                        "score": 91.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 08:00:00",
                    },
                    {
                        "title": "淘汰文章",
                        "source": "xinhua",
                        "url": "https://example.com/b",
                        "summary": "摘要B",
                        "score": 88.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 08:10:00",
                    },
                ],
                "deduped_articles": [
                    {
                        "title": "保留文章",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
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

    assert html.count('data-stage-view=') == 1
    assert "保留文章" in html
    assert "淘汰文章" in html
    assert "阶段选择" in html
    assert "阶段前聚合结果" in html
    assert "阶段后保留结果" in html


def test_build_dashboard_html_stage_details_use_master_detail_layout() -> None:
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
                        "title": "保留文章",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
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

    assert "阶段摘要" in html
    assert "主视区" in html
    assert "次级差异" in html
    assert 'class="stage-summary-strip"' in html


def test_build_dashboard_html_stage_primary_workspace_uses_asymmetric_compare_board() -> None:
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
                "raw_articles": [
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

    assert 'class="stage-compare-pair is-asymmetric"' in html
    assert 'class="stage-compare-panel is-before"' in html
    assert 'class="stage-compare-panel is-after"' in html
    assert 'class="article-stack is-dense"' in html
    assert 'class="article-stack is-focus"' in html


def test_build_stage_compare_payload_reports_removed_items_and_rank_changes() -> None:
    stage_options, active_view = _build_stage_compare_payload(
        {
            "stages": {
                "raw_articles": [
                    {
                        "title": "文章 A",
                        "source": "people_daily",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
                        "score": 91.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:00:00",
                    },
                    {
                        "title": "文章 B",
                        "source": "xinhua",
                        "url": "https://example.com/b",
                        "summary": "摘要B",
                        "score": 88.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:10:00",
                    },
                ],
                "filtered_articles": [
                    {
                        "title": "文章 B",
                        "source": "xinhua",
                        "url": "https://example.com/b",
                        "summary": "摘要B",
                        "score": 88.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:10:00",
                    }
                ],
                "deduped_articles": [],
                "chosen_articles": [],
            }
        }
    )

    filtered_view = next(option for option in stage_options if option["key"] == "filtered_articles")
    assert active_view is filtered_view
    assert [item["title"] for item in filtered_view["removed_items"]] == ["文章 A"]
    assert filtered_view["rank_changes"][0]["title"] == "文章 B"
    assert filtered_view["rank_changes"][0]["before_rank"] == 2
    assert filtered_view["rank_changes"][0]["after_rank"] == 1


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
            "time_strategies": ["source_day", "source_window"],
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
    assert "时间策略：source_day / source_window" in html
    assert "去重策略：aggressive" in html


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
            "stages": {
                "raw_articles": [],
                "filtered_articles": [],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "核心统计" in html
    assert "阶段转化" in html
    assert "运行配置" in html
    assert "产物入口" in html
    assert "people_daily" in html


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
            "stages": {
                "raw_articles": [],
                "filtered_articles": [],
                "deduped_articles": [],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert 'class="summary-source-badges"' in html
    assert "原始 -> 过滤后" in html
    assert "过滤后 -> 最终入选" in html


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
    assert 'name="blocked_keywords"' in html
    assert 'name="time_strategy"' in html
    assert 'name="dedupe_strategy"' in html


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


def test_build_dashboard_preview_html_supports_stage_compare_and_collapsible_details() -> None:
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

    assert 'data-default-stage="filtered_articles"' in html
    assert "<details" in html
    assert "xinhua" in html
    assert "展开摘要" in html


def test_build_dashboard_preview_html_includes_stage_toggle_script() -> None:
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


def test_build_dashboard_html_stage_details_collapse_secondary_diffs() -> None:
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
                "raw_articles": [
                    {
                        "title": "文章 A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要 A",
                        "score": 91.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 08:00:00",
                    },
                    {
                        "title": "文章 B",
                        "source": "xinhua",
                        "url": "https://example.com/b",
                        "summary": "摘要 B",
                        "score": 89.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 08:05:00",
                    },
                ],
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

    assert "删除条目（可展开）" in html
    assert "排序变化（可展开）" in html
    assert html.count('class="stage-secondary-details"') >= 2


def test_build_dashboard_preview_html_places_stage_compare_data_inside_shell() -> None:
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
            "raw_count": 1,
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
        },
        error_message="",
    )

    parser = _StageCompareDataPlacementParser()
    parser.feed(html)

    assert parser.stage_data_inside_shell is True


def test_build_dashboard_preview_html_matches_master_detail_stage_layout() -> None:
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

    assert "阶段摘要" in html
    assert "主视区" in html
    assert "次级差异" in html
    assert "删除条目（可展开）" in html


def test_build_dashboard_preview_html_uses_asymmetric_compare_board() -> None:
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
                "raw_articles": [
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

    assert 'class="stage-compare-pair is-asymmetric"' in html
    assert 'class="stage-compare-panel is-before"' in html
    assert 'class="stage-compare-panel is-after"' in html
    assert 'class="article-stack is-dense"' in html
    assert 'class="article-stack is-focus"' in html


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


def test_build_dashboard_html_places_stage_compare_data_inside_shell() -> None:
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
            "raw_count": 1,
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
        },
        error_message="",
    )

    parser = _StageCompareDataPlacementParser()
    parser.feed(html)

    assert parser.stage_data_inside_shell is True


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
                    {
                        "title": "文章 A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
                        "score": 91.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:00:00",
                    },
                    {
                        "title": "文章 B",
                        "source": "xinhua",
                        "url": "https://example.com/b",
                        "summary": "摘要B",
                        "score": 88.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:10:00",
                    },
                ],
                "deduped_articles": [
                    {
                        "title": "文章 A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
                        "score": 91.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:00:00",
                    }
                ],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert "删除 1" in html
    assert "查看重复项收敛结果" in html


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

    assert "function switchStageCompare" in html
    assert 'data-stage="chosen_articles"' in html
    assert "文章1" in html
    assert "展开摘要" in html


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
                    {
                        "title": "文章 A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
                        "score": 91.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:00:00",
                    },
                    {
                        "title": "文章 B",
                        "source": "xinhua",
                        "url": "https://example.com/b",
                        "summary": "摘要B",
                        "score": 88.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:10:00",
                    },
                ],
                "deduped_articles": [
                    {
                        "title": "文章 A",
                        "source": "xinhua",
                        "url": "https://example.com/a",
                        "summary": "摘要A",
                        "score": 91.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:00:00",
                    }
                ],
                "chosen_articles": [],
            },
        },
        error_message="",
    )

    assert html.count('data-stage-view=') == 1
    assert "阶段后保留结果" in html
    assert "核心统计" in html
    assert "产物入口" in html


def test_dashboard_handler_posts_selected_strategies_to_run_digest() -> None:
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.path = "/run"
    body = (
        b"sources=xinhua&filter_strategy=strict&blocked_keywords=%E4%B9%A0%E8%BF%91%E5%B9%B3%EF%BC%8C%E6%9D%8E%E5%BC%BA"
        b"&time_strategy=source_day&time_strategy=source_window&dedupe_strategy=aggressive"
    )
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
            "time_strategies": ["source_day", "source_window"],
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
        blocked_keywords=["习近平", "李强"],
        time_strategies=["source_day", "source_window"],
        dedupe_strategy="aggressive",
    )


def test_dashboard_handler_post_persists_submitted_preferences() -> None:
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.path = "/run"
    body = (
        b"sources=xinhua&filter_strategy=strict&blocked_keywords=%E4%B9%A0%E8%BF%91%E5%B9%B3%EF%BC%8C%E6%9D%8E%E5%BC%BA"
        b"&time_strategy=source_day&dedupe_strategy=aggressive"
    )
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.send_response = lambda code: None
    handler.send_header = lambda key, value: None
    handler.end_headers = lambda: None
    handler._write_html = lambda html: None

    mock_store = SimpleNamespace(
        save_dashboard_preferences=lambda **kwargs: None,
        get_dashboard_preferences=lambda: None,
    )

    with patch("app.dashboard_server._build_state_store", return_value=mock_store), patch(
        "app.dashboard_server.run_digest"
    ) as mock_run_digest, patch.object(mock_store, "save_dashboard_preferences") as mock_save_preferences:
        mock_run_digest.return_value = {
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "strict",
            "time_strategies": ["source_day"],
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

    mock_save_preferences.assert_called_once_with(
        selected_sources=["xinhua"],
        filter_strategy="strict",
        blocked_keywords_text="习近平，李强",
        time_strategies=["source_day"],
        dedupe_strategy="aggressive",
    )


def test_dashboard_handler_post_preserves_empty_blocked_keywords() -> None:
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.path = "/run"
    body = (
        b"sources=xinhua&filter_strategy=strict&blocked_keywords="
        b"&time_strategy=source_day&dedupe_strategy=aggressive"
    )
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.send_response = lambda code: None
    handler.send_header = lambda key, value: None
    handler.end_headers = lambda: None
    handler._write_html = lambda html: None

    mock_store = SimpleNamespace(
        save_dashboard_preferences=lambda **kwargs: None,
        get_dashboard_preferences=lambda: None,
    )

    with patch("app.dashboard_server._build_state_store", return_value=mock_store), patch(
        "app.dashboard_server.run_digest"
    ) as mock_run_digest, patch.object(mock_store, "save_dashboard_preferences") as mock_save_preferences:
        mock_run_digest.return_value = {
            "digest_date": "2026-05-11",
            "source_date": "2026-05-10",
            "selected_sources": ["xinhua"],
            "filter_strategy": "strict",
            "time_strategies": ["source_day"],
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

    mock_save_preferences.assert_called_once_with(
        selected_sources=["xinhua"],
        filter_strategy="strict",
        blocked_keywords_text="",
        time_strategies=["source_day"],
        dedupe_strategy="aggressive",
    )
    mock_run_digest.assert_called_once_with(
        selected_sources=["xinhua"],
        filter_strategy="strict",
        blocked_keywords=[],
        time_strategies=["source_day"],
        dedupe_strategy="aggressive",
    )


def test_build_dashboard_html_stage_details_show_kept_and_removed_articles() -> None:
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
                "raw_articles": [
                    {
                        "title": "保留文章",
                        "source": "xinhua",
                        "url": "https://example.com/keep",
                        "summary": "摘要A",
                        "score": 91.0,
                        "tags": ["民生"],
                        "published_at": "2026-05-10 08:00:00",
                    },
                    {
                        "title": "过滤文章",
                        "source": "xinhua",
                        "url": "https://example.com/remove",
                        "summary": "摘要B",
                        "score": 60.0,
                        "tags": [],
                        "published_at": "2026-05-10 08:10:00",
                    },
                ],
                "filtered_articles": [
                    {
                        "title": "保留文章",
                        "source": "xinhua",
                        "url": "https://example.com/keep",
                        "summary": "摘要A",
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

    assert "阶段后保留结果" in html
    assert "删除条目" in html
    assert "过滤文章" in html
    assert "保留文章" in html


def test_dashboard_handler_default_sources_include_people_app() -> None:
    assert "people_app" in DashboardHandler.default_sources


def test_dashboard_handler_get_prefills_persisted_preferences() -> None:
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.path = "/"
    handler.wfile = io.BytesIO()
    html_chunks: list[str] = []
    handler._write_html = lambda html: html_chunks.append(html)

    with patch("app.dashboard_server.StateStore") as mock_state_store:
        mock_state_store.return_value.get_dashboard_preferences.return_value = {
            "selected_sources": ["xinhua"],
            "filter_strategy": "strict",
            "blocked_keywords_text": "习近平，李强",
            "time_strategies": ["source_day", "source_window"],
            "dedupe_strategy": "aggressive",
        }

        handler.do_GET()

    html = html_chunks[0]
    assert 'value="xinhua"' in html
    assert 'name="blocked_keywords"' in html
    assert "习近平，李强" in html
    assert "value=\"strict\" selected" in html
    assert "value=\"aggressive\" selected" in html


def test_dashboard_handler_get_keeps_empty_persisted_blocked_keywords() -> None:
    handler = DashboardHandler.__new__(DashboardHandler)
    handler.path = "/"
    handler.wfile = io.BytesIO()
    html_chunks: list[str] = []
    handler._write_html = lambda html: html_chunks.append(html)

    mock_store = SimpleNamespace(
        get_dashboard_preferences=lambda: {
            "selected_sources": ["xinhua"],
            "filter_strategy": "strict",
            "blocked_keywords_text": "",
            "time_strategies": ["source_day"],
            "dedupe_strategy": "aggressive",
        }
    )

    with patch("app.dashboard_server._build_state_store", return_value=mock_store):
        handler.do_GET()

    html = html_chunks[0]
    assert '<textarea name="blocked_keywords" rows="3" placeholder="用逗号、顿号或换行分隔"></textarea>' in html


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
            time_strategies=["source_day", "source_window"],
            dedupe_strategy="aggressive",
        )

    assert result["filter_strategy"] == "strict"
    assert result["time_strategies"] == ["source_day", "source_window"]
    assert result["dedupe_strategy"] == "aggressive"


def test_run_digest_forwards_blocked_keywords_to_filter_articles() -> None:
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
    ) as mock_filter_articles, patch("app.main.score_articles", return_value=[]), patch(
        "app.main.deduplicate_articles", return_value=[]
    ), patch("app.main.build_digest_draft") as mock_build_digest_draft, patch(
        "app.main.render_digest_html", return_value="<html></html>"
    ), patch("app.main.publish_digest", return_value=("skipped", "")):
        mock_build_digest_draft.return_value = SimpleNamespace(
            digest_date="2026-05-11",
            html="",
        )

        run_digest(
            selected_sources=["xinhua"],
            blocked_keywords=["两会"],
        )

    mock_filter_articles.assert_called_once_with(
        [],
        strategy="standard",
        blocked_keywords=["两会"],
        time_strategies=["source_day"],
        source_date="2026-05-10",
        digest_date="2026-05-11",
        window_start="19:30",
        window_end="22:30",
    )
