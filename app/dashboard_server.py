from __future__ import annotations

import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import AppConfig
from app.main import run_digest
from app.pipeline.filter import DEFAULT_BLOCKED_KEYWORDS
from app.pipeline.time_filter import TIME_STRATEGY_OPTIONS
from app.sources.registry import list_available_sources
from app.storage.state import StateStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STAGE_SECTIONS = [
    {"key": "raw_articles", "label": "获取"},
    {"key": "filtered_articles", "label": "过滤"},
    {"key": "deduped_articles", "label": "去重"},
    {"key": "chosen_articles", "label": "入选"},
]
STAGE_PAIR_OPTIONS = [
    {
        "key": "raw_articles",
        "button_label": "获取",
        "button_meta": "查看各源抓取聚合结果",
        "previous_key": None,
        "previous_label": "各源抓取聚合",
        "previous_hint": "抓取入池后的候选基线",
        "current_key": "raw_articles",
        "current_label": "获取阶段结果",
        "current_hint": "已进入候选池",
        "status_copy": "抓取入池",
        "removed_reason": "获取阶段不做淘汰",
    },
    {
        "key": "filtered_articles",
        "button_label": "过滤",
        "button_meta": "查看过滤前后差异",
        "previous_key": "raw_articles",
        "previous_label": "过滤前聚合结果",
        "previous_hint": "抓取聚合后的候选全量",
        "current_key": "filtered_articles",
        "current_label": "过滤后结果",
        "current_hint": "通过主题与黑名单过滤",
        "status_copy": "通过主题与黑名单过滤",
        "removed_reason": "未通过主题过滤或命中黑名单",
    },
    {
        "key": "deduped_articles",
        "button_label": "去重",
        "button_meta": "查看重复项收敛结果",
        "previous_key": "filtered_articles",
        "previous_label": "去重前聚合结果",
        "previous_hint": "过滤后进入去重的候选全量",
        "current_key": "deduped_articles",
        "current_label": "去重后结果",
        "current_hint": "通过去重校验",
        "status_copy": "通过去重校验",
        "removed_reason": "命中重复项，被本轮去重淘汰",
    },
    {
        "key": "chosen_articles",
        "button_label": "入选",
        "button_meta": "查看最终排序结果",
        "previous_key": "deduped_articles",
        "previous_label": "入选前聚合结果",
        "previous_hint": "去重后待排序候选",
        "current_key": "chosen_articles",
        "current_label": "最终入选结果",
        "current_hint": "进入最终晨报草稿",
        "status_copy": "进入最终晨报草稿",
        "removed_reason": "未进入最终排序结果",
    },
]
DEFAULT_STAGE_PAIR_KEY = "filtered_articles"
PREVIEW_DESIGN_A_PATH = "/preview/design-a"
PREVIEW_DESIGN_A_RUN_PATH = "/preview/design-a/run"


def build_artifact_url(path: str | Path) -> str:
    artifact_path = Path(path)
    return f"/artifacts/{artifact_path.as_posix()}"


def resolve_artifact_path(request_path: str) -> Path:
    relative = unquote(request_path.removeprefix("/artifacts/")).lstrip("/")
    return Path(relative)


def _article_identity(article: dict[str, object]) -> str:
    url = str(article.get("url") or "").strip()
    if url:
        return url
    title = str(article.get("title") or "").strip()
    source = str(article.get("source") or "").strip()
    return f"{title}::{source}"


def _source_breakdown(items: list[dict[str, object]]) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    order: list[str] = []
    for article in items:
        source = str(article.get("source") or "未知来源").strip() or "未知来源"
        if source not in counts:
            counts[source] = 0
            order.append(source)
        counts[source] += 1
    return [{"source": source, "count": counts[source]} for source in order]


def _format_blocked_keywords(keywords: list[str] | tuple[str, ...] | None) -> str:
    if not keywords:
        return ""
    return "，".join(keyword.strip() for keyword in keywords if keyword.strip())


def _parse_blocked_keywords(raw_value: str | None) -> list[str]:
    if raw_value is None:
        return list(DEFAULT_BLOCKED_KEYWORDS)
    parts = re.split(r"[\s,，、;；]+", raw_value)
    normalized: list[str] = []
    seen: set[str] = set()
    for part in parts:
        keyword = part.strip()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        normalized.append(keyword)
    return normalized


def _build_stage_compare_payload(result: dict[str, object] | None) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    if not result:
        return STAGE_PAIR_OPTIONS, None

    stages = result.get("stages", {})
    if not isinstance(stages, dict):
        return STAGE_PAIR_OPTIONS, None

    stage_pairs: list[dict[str, object]] = []
    active_pair: dict[str, object] | None = None
    for option in STAGE_PAIR_OPTIONS:
        if option["previous_key"] is None:
            previous_items = list(stages.get(option["current_key"], []))
        else:
            previous_items = list(stages.get(option["previous_key"], []))
        current_items = list(stages.get(option["current_key"], []))
        previous_rank_map = {_article_identity(article): index + 1 for index, article in enumerate(previous_items)}
        current_rank_map = {_article_identity(article): index + 1 for index, article in enumerate(current_items)}
        current_keys = set(current_rank_map)
        passed_items = [article for article in current_items if _article_identity(article) in previous_rank_map]
        removed_items = [article for article in previous_items if _article_identity(article) not in current_keys]
        rank_changes = []
        for article in current_items:
            identity = _article_identity(article)
            if identity not in previous_rank_map:
                continue
            before_rank = previous_rank_map[identity]
            after_rank = current_rank_map[identity]
            rank_delta = before_rank - after_rank
            direction = "不变"
            if rank_delta > 0:
                direction = "上升"
            elif rank_delta < 0:
                direction = "下降"
            rank_changes.append(
                {
                    "title": article.get("title"),
                    "source": article.get("source"),
                    "url": article.get("url"),
                    "before_rank": before_rank,
                    "after_rank": after_rank,
                    "rank_delta": rank_delta,
                    "direction": direction,
                }
            )
        after_items = []
        for article in current_items:
            identity = _article_identity(article)
            before_rank = previous_rank_map.get(identity)
            after_rank = current_rank_map.get(identity)
            article_payload = dict(article)
            article_payload["before_rank"] = before_rank
            article_payload["after_rank"] = after_rank
            article_payload["rank_delta"] = None if before_rank is None or after_rank is None else before_rank - after_rank
            after_items.append(article_payload)
        pair_payload = {
            **option,
            "before_items": previous_items,
            "after_items": after_items,
            "current_items": after_items,
            "previous_items": previous_items,
            "passed_items": passed_items,
            "removed_items": removed_items,
            "rank_changes": rank_changes,
            "previous_count": len(previous_items),
            "current_count": len(after_items),
            "after_count": len(after_items),
            "passed_count": len(after_items),
            "removed_count": len(removed_items),
            "rank_change_count": sum(1 for item in rank_changes if item["rank_delta"] != 0),
            "before_breakdown": _source_breakdown(previous_items),
            "after_breakdown": _source_breakdown(after_items),
        }
        stage_pairs.append(pair_payload)
        if option["key"] == DEFAULT_STAGE_PAIR_KEY:
            active_pair = pair_payload

    return stage_pairs, active_pair


def _build_state_store() -> StateStore:
    config = AppConfig()
    config.ensure_directories()
    return StateStore(config.data_dir / "state.db", PROJECT_ROOT / "app/storage/schema.sql")


def _render_dashboard_template(
    template_name: str,
    *,
    available_sources: list[dict[str, str]],
    selected_sources: list[str],
    selected_filter_strategy: str = "standard",
    selected_blocked_keywords_text: str | None = None,
    selected_time_strategies: list[str] | None = None,
    selected_dedupe_strategy: str = "standard",
    result: dict[str, object] | None,
    error_message: str,
) -> str:
    templates_dir = Path(__file__).resolve().parent / "templates"
    environment = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    stage_compare_options, active_stage_compare = _build_stage_compare_payload(result)
    template = environment.get_template(template_name)
    return template.render(
        available_sources=available_sources,
        available_time_strategies=TIME_STRATEGY_OPTIONS,
        selected_sources=selected_sources,
        selected_filter_strategy=selected_filter_strategy,
        selected_blocked_keywords_text=(
            _format_blocked_keywords(DEFAULT_BLOCKED_KEYWORDS)
            if selected_blocked_keywords_text is None
            else selected_blocked_keywords_text
        ),
        selected_time_strategies=selected_time_strategies or ["source_day"],
        selected_dedupe_strategy=selected_dedupe_strategy,
        result=result,
        error_message=error_message,
        stage_sections=STAGE_SECTIONS,
        stage_compare_options=stage_compare_options,
        active_stage_compare=active_stage_compare,
        default_stage_pair_key=DEFAULT_STAGE_PAIR_KEY,
        stage_compare_json=json.dumps(stage_compare_options, ensure_ascii=False),
    )


def build_dashboard_html(
    *,
    available_sources: list[dict[str, str]],
    selected_sources: list[str],
    selected_filter_strategy: str = "standard",
    selected_blocked_keywords_text: str | None = None,
    selected_time_strategies: list[str] | None = None,
    selected_dedupe_strategy: str = "standard",
    result: dict[str, object] | None,
    error_message: str,
) -> str:
    return _render_dashboard_template(
        "dashboard.html.j2",
        available_sources=available_sources,
        selected_sources=selected_sources,
        selected_filter_strategy=selected_filter_strategy,
        selected_blocked_keywords_text=selected_blocked_keywords_text,
        selected_time_strategies=selected_time_strategies,
        selected_dedupe_strategy=selected_dedupe_strategy,
        result=result,
        error_message=error_message,
    )


def build_dashboard_preview_html(
    *,
    available_sources: list[dict[str, str]],
    selected_sources: list[str],
    selected_filter_strategy: str = "standard",
    selected_blocked_keywords_text: str | None = None,
    selected_time_strategies: list[str] | None = None,
    selected_dedupe_strategy: str = "standard",
    result: dict[str, object] | None,
    error_message: str,
) -> str:
    return _render_dashboard_template(
        "dashboard_preview_a.html.j2",
        available_sources=available_sources,
        selected_sources=selected_sources,
        selected_filter_strategy=selected_filter_strategy,
        selected_blocked_keywords_text=selected_blocked_keywords_text,
        selected_time_strategies=selected_time_strategies,
        selected_dedupe_strategy=selected_dedupe_strategy,
        result=result,
        error_message=error_message,
    )


class DashboardHandler(BaseHTTPRequestHandler):
    default_sources = ["people_daily", "people_app", "cctv", "xinhua"]

    def _write_html(self, html: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _write_file(self, file_path: Path) -> None:
        content_type, _ = mimetypes.guess_type(str(file_path))
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def _serve_artifact(self) -> None:
        artifact_relative = resolve_artifact_path(self.path)
        artifact_path = (PROJECT_ROOT / artifact_relative).resolve()
        try:
            artifact_path.relative_to(PROJECT_ROOT)
        except ValueError:
            self.send_error(403, "Forbidden")
            return
        if not artifact_path.is_file():
            self.send_error(404, "Not Found")
            return
        self._write_file(artifact_path)

    def _render_page(
        self,
        *,
        preview: bool,
        selected_sources: list[str],
        selected_filter_strategy: str = "standard",
        selected_blocked_keywords_text: str | None = None,
        selected_time_strategies: list[str] | None = None,
        selected_dedupe_strategy: str = "standard",
        result: dict[str, object] | None,
        error_message: str,
    ) -> str:
        builder = build_dashboard_preview_html if preview else build_dashboard_html
        return builder(
            available_sources=list_available_sources(),
            selected_sources=selected_sources,
            selected_filter_strategy=selected_filter_strategy,
            selected_blocked_keywords_text=selected_blocked_keywords_text,
            selected_time_strategies=selected_time_strategies,
            selected_dedupe_strategy=selected_dedupe_strategy,
            result=result,
            error_message=error_message,
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/artifacts/"):
            self._serve_artifact()
            return
        preview = self.path == PREVIEW_DESIGN_A_PATH
        preferences = _build_state_store().get_dashboard_preferences() or {}
        html = self._render_page(
            preview=preview,
            selected_sources=preferences.get("selected_sources", self.default_sources),
            selected_filter_strategy=preferences.get("filter_strategy", "standard"),
            selected_blocked_keywords_text=preferences.get(
                "blocked_keywords_text",
                _format_blocked_keywords(DEFAULT_BLOCKED_KEYWORDS),
            ),
            selected_time_strategies=preferences.get("time_strategies", ["source_day"]),
            selected_dedupe_strategy=preferences.get("dedupe_strategy", "standard"),
            result=None,
            error_message="",
        )
        self._write_html(html)

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(body, keep_blank_values=True)
        selected_sources = form.get("sources") or self.default_sources
        filter_strategy = (form.get("filter_strategy") or ["standard"])[0]
        blocked_keywords_text = (form.get("blocked_keywords") or [None])[0]
        blocked_keywords = _parse_blocked_keywords(blocked_keywords_text)
        normalized_blocked_keywords_text = _format_blocked_keywords(blocked_keywords)
        time_strategies = form.get("time_strategy") or []
        dedupe_strategy = (form.get("dedupe_strategy") or ["standard"])[0]
        error_message = ""
        result: dict[str, object] | None = None
        preview = self.path == PREVIEW_DESIGN_A_RUN_PATH
        _build_state_store().save_dashboard_preferences(
            selected_sources=selected_sources,
            filter_strategy=filter_strategy,
            blocked_keywords_text=normalized_blocked_keywords_text,
            time_strategies=time_strategies,
            dedupe_strategy=dedupe_strategy,
        )
        try:
            result = run_digest(
                selected_sources=selected_sources,
                filter_strategy=filter_strategy,
                blocked_keywords=blocked_keywords,
                time_strategies=time_strategies,
                dedupe_strategy=dedupe_strategy,
            )
        except Exception as exc:  # pragma: no cover - first version only surfaces error text
            error_message = str(exc)
        html = self._render_page(
            preview=preview,
            selected_sources=selected_sources,
            selected_filter_strategy=filter_strategy,
            selected_blocked_keywords_text=normalized_blocked_keywords_text,
            selected_time_strategies=time_strategies,
            selected_dedupe_strategy=dedupe_strategy,
            result=result,
            error_message=error_message,
        )
        self._write_html(html)


def serve_dashboard(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"dashboard=http://{host}:{port}/")
    server.serve_forever()


if __name__ == "__main__":
    serve_dashboard()
