from __future__ import annotations

import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.main import run_digest
from app.sources.registry import list_available_sources


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STAGE_SECTIONS = [
    {"key": "raw_articles", "label": "原始候选明细"},
    {"key": "filtered_articles", "label": "过滤后明细"},
    {"key": "deduped_articles", "label": "去重后明细"},
    {"key": "chosen_articles", "label": "最终入选明细"},
]
PREVIEW_DESIGN_A_PATH = "/preview/design-a"
PREVIEW_DESIGN_A_RUN_PATH = "/preview/design-a/run"


def build_artifact_url(path: str | Path) -> str:
    artifact_path = Path(path)
    return f"/artifacts/{artifact_path.as_posix()}"


def resolve_artifact_path(request_path: str) -> Path:
    relative = unquote(request_path.removeprefix("/artifacts/")).lstrip("/")
    return Path(relative)


def _render_dashboard_template(
    template_name: str,
    *,
    available_sources: list[dict[str, str]],
    selected_sources: list[str],
    selected_filter_strategy: str = "standard",
    selected_dedupe_strategy: str = "standard",
    result: dict[str, object] | None,
    error_message: str,
) -> str:
    templates_dir = Path(__file__).resolve().parent / "templates"
    environment = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = environment.get_template(template_name)
    return template.render(
        available_sources=available_sources,
        selected_sources=selected_sources,
        selected_filter_strategy=selected_filter_strategy,
        selected_dedupe_strategy=selected_dedupe_strategy,
        result=result,
        error_message=error_message,
        stage_sections=STAGE_SECTIONS,
    )


def build_dashboard_html(
    *,
    available_sources: list[dict[str, str]],
    selected_sources: list[str],
    selected_filter_strategy: str = "standard",
    selected_dedupe_strategy: str = "standard",
    result: dict[str, object] | None,
    error_message: str,
) -> str:
    return _render_dashboard_template(
        "dashboard.html.j2",
        available_sources=available_sources,
        selected_sources=selected_sources,
        selected_filter_strategy=selected_filter_strategy,
        selected_dedupe_strategy=selected_dedupe_strategy,
        result=result,
        error_message=error_message,
    )


def build_dashboard_preview_html(
    *,
    available_sources: list[dict[str, str]],
    selected_sources: list[str],
    selected_filter_strategy: str = "standard",
    selected_dedupe_strategy: str = "standard",
    result: dict[str, object] | None,
    error_message: str,
) -> str:
    return _render_dashboard_template(
        "dashboard_preview_a.html.j2",
        available_sources=available_sources,
        selected_sources=selected_sources,
        selected_filter_strategy=selected_filter_strategy,
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
        selected_dedupe_strategy: str = "standard",
        result: dict[str, object] | None,
        error_message: str,
    ) -> str:
        builder = build_dashboard_preview_html if preview else build_dashboard_html
        return builder(
            available_sources=list_available_sources(),
            selected_sources=selected_sources,
            selected_filter_strategy=selected_filter_strategy,
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
        dedupe_strategy = (form.get("dedupe_strategy") or ["standard"])[0]
        error_message = ""
        result: dict[str, object] | None = None
        preview = self.path == PREVIEW_DESIGN_A_RUN_PATH
        try:
            result = run_digest(
                selected_sources=selected_sources,
                filter_strategy=filter_strategy,
                dedupe_strategy=dedupe_strategy,
            )
        except Exception as exc:  # pragma: no cover - first version only surfaces error text
            error_message = str(exc)
        html = self._render_page(
            preview=preview,
            selected_sources=selected_sources,
            selected_filter_strategy=filter_strategy,
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
