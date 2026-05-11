from __future__ import annotations

import json

from app.config import AppConfig
from app.models import DigestDraft


def publish_digest(config: AppConfig, draft: DigestDraft, html: str) -> tuple[str, str]:
    if config.publish_mode != "auto":
        return "skipped", "manual mode enabled; draft generated only"

    if not config.wechat_app_id or not config.wechat_app_secret:
        return "skipped", "wechat credentials missing; skipped auto publish"

    payload = {
        "title": draft.title,
        "intro": draft.intro,
        "items": len(draft.items),
        "html_length": len(html),
    }
    payload_path = config.output_dir / f"{draft.digest_date}-wechat-payload.json"
    payload_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return "prepared", f"wechat payload prepared at {payload_path}"
