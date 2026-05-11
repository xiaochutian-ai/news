from __future__ import annotations

from app.config import AppConfig
from app.sources.cctv import CCTVAdapter
from app.sources.people_daily import PeopleDailyAdapter


def build_source_adapters(config: AppConfig) -> list[object]:
    adapters: list[object] = []
    if config.people_daily_enabled:
        adapters.append(PeopleDailyAdapter())
    if config.cctv_enabled:
        adapters.append(CCTVAdapter())
    return adapters
