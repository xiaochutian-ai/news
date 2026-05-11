from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import DigestDraft


def render_digest_html(template_dir: Path, draft: DigestDraft) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("digest.html.j2")
    return template.render(draft=draft)
