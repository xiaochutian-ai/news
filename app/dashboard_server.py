from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.main import run_digest
from app.pipeline.time_filter import TIME_STRATEGY_OPTIONS
from app.sources.registry import list_available_sources


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STAGE_SECTIONS = [
    {"key": "raw_articles", "label": "原始候选明细"},
    {"key": "filtered_articles", "label": "过滤后明细"},
    {"key": "deduped_articles", "label": "去重后明细"},
    {"key": "chosen_articles", "label": "最终入选明细"},
]
STAGE_PAIR_OPTIONS = [
    {
        "key": "filtered_articles",
        "button_label": "过滤后明细",
        "button_meta": "查看原始候选与过滤后",
        "previous_key": "raw_articles",
        "previous_label": "原始候选明细",
        "previous_hint": "过滤前候选",
        "current_key": "filtered_articles",
        "current_label": "过滤后明细",
        "current_hint": "通过主题过滤",
        "status_copy": "通过主题过滤",
    },
    {
        "key": "deduped_articles",
        "button_label": "去重后明细",
        "button_meta": "默认对比阶段",
        "previous_key": "filtered_articles",
        "previous_label": "过滤后明细",
        "previous_hint": "去重前结果",
        "current_key": "deduped_articles",
        "current_label": "去重后明细",
        "current_hint": "通过去重校验",
        "status_copy": "通过去重校验",
    },
    {
        "key": "chosen_articles",
        "button_label": "最终入选明细",
        "button_meta": "查看最终入选结果",
        "previous_key": "deduped_articles",
        "previous_label": "去重后明细",
        "previous_hint": "入选前候选",
        "current_key": "chosen_articles",
        "current_label": "最终入选明细",
        "current_hint": "进入最终晨报草稿",
        "status_copy": "进入最终晨报草稿",
    },
]
DEFAULT_STAGE_PAIR_KEY = "deduped_articles"
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


def _build_stage_compare_payload(result: dict[str, object] | None) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    if not result:
        return STAGE_PAIR_OPTIONS, None

    stages = result.get("stages", {})
    if not isinstance(stages, dict):
        return STAGE_PAIR_OPTIONS, None

    stage_pairs: list[dict[str, object]] = []
    active_pair: dict[str, object] | None = None
    for option in STAGE_PAIR_OPTIONS:
        previous_items = list(stages.get(option["previous_key"], []))
        current_items = list(stages.get(option["current_key"], []))
        current_keys = {_article_identity(article) for article in current_items}
        passed_items = [article for article in previous_items if _article_identity(article) in current_keys]
        pair_payload = {
            **option,
            "previous_items": previous_items,
            "passed_items": passed_items,
            "previous_count": len(previous_items),
            "passed_count": len(passed_items),
            "removed_count": max(len(previous_items) - len(passed_items), 0),
        }
        stage_pairs.append(pair_payload)
        if option["key"] == DEFAULT_STAGE_PAIR_KEY:
            active_pair = pair_payload

    return stage_pairs, active_pair


def _render_dashboard_template(
    template_name: str,
    *,
    available_sources: list[dict[str, str]],
    selected_sources: list[str],
    selected_filter_strategy: str = "standard",
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
        html = self._render_page(
            preview=preview,
            selected_sources=self.default_sources,
            selected_filter_strategy="standard",
            selected_time_strategies=["source_day"],
            selected_dedupe_strategy="standard",
            result=None,
            error_message="",
        )
        self._write_html(html)

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(body)
        selected_sources = form.get("sources") or self.default_sources
        filter_strategy = (form.get("filter_strategy") or ["standard"])[0]
        time_strategies = form.get("time_strategy") or []
        dedupe_strategy = (form.get("dedupe_strategy") or ["standard"])[0]
        error_message = ""
        result: dict[str, object] | None = None
        preview = self.path == PREVIEW_DESIGN_A_RUN_PATH
        try:
            result = run_digest(
                selected_sources=selected_sources,
                filter_strategy=filter_strategy,
                time_strategies=time_strategies,
                dedupe_strategy=dedupe_strategy,
            )
        except Exception as exc:  # pragma: no cover - first version only surfaces error text
            error_message = str(exc)
        html = self._render_page(
            preview=preview,
            selected_sources=selected_sources,
            selected_filter_strategy=filter_strategy,
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
