from __future__ import annotations

from app.config import AppConfig
from app.sources.cctv import CCTVAdapter
from app.sources.people_daily import PeopleDailyAdapter
from app.sources.xinhua import XinhuaAdapter


SOURCE_BUILDERS = {
    "people_daily": PeopleDailyAdapter,
    "cctv": CCTVAdapter,
    "xinhua": XinhuaAdapter,
}


def list_available_sources() -> list[dict[str, str]]:
    return [
        {"key": "people_daily", "label": "人民日报"},
        {"key": "cctv", "label": "央视"},
        {"key": "xinhua", "label": "新华社"},
    ]


def build_source_adapters(
    config: AppConfig,
    selected_sources: list[str] | None = None,
) -> list[object]:
    if selected_sources is not None:
        return [SOURCE_BUILDERS[key]() for key in selected_sources if key in SOURCE_BUILDERS]

    adapters: list[object] = []
    if config.people_daily_enabled:
        adapters.append(PeopleDailyAdapter())
    if config.cctv_enabled:
        adapters.append(CCTVAdapter())
    if getattr(config, "xinhua_enabled", True):
        adapters.append(XinhuaAdapter())
    return adapters
