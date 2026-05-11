from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    publish_mode: str = os.getenv("PUBLISH_MODE", "manual")
    schedule_cron: str = os.getenv("SCHEDULE_CRON", "30 22 * * *")
    window_start: str = os.getenv("WINDOW_START", "19:30")
    window_end: str = os.getenv("WINDOW_END", "22:30")
    max_items_per_digest: int = int(os.getenv("MAX_ITEMS_PER_DIGEST", "7"))
    min_score_to_publish: float = float(os.getenv("MIN_SCORE_TO_PUBLISH", "78"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "output/drafts"))
    data_dir: Path = Path(os.getenv("DATA_DIR", "data/app"))
    people_daily_enabled: bool = os.getenv("PEOPLE_DAILY_ENABLED", "true").lower() == "true"
    people_app_enabled: bool = os.getenv("PEOPLE_APP_ENABLED", "true").lower() == "true"
    cctv_enabled: bool = os.getenv("CCTV_ENABLED", "true").lower() == "true"
    wechat_app_id: str = os.getenv("WECHAT_APP_ID", "")
    wechat_app_secret: str = os.getenv("WECHAT_APP_SECRET", "")
    wechat_cover_media_id: str = os.getenv("WECHAT_MEDIA_ID_COVER", "")

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)


def build_digest_context(digest_date: date | None = None) -> dict[str, str]:
    digest_day = digest_date or date.today()
    source_day = digest_day - timedelta(days=1)
    return {
        "digest_date": digest_day.isoformat(),
        "source_date": source_day.isoformat(),
        "window_label": f"{source_day.isoformat()} 19:30-22:30",
        "source_day_compact": source_day.strftime("%Y%m%d"),
    }
