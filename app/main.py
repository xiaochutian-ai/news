from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.config import AppConfig, build_digest_context
from app.models import DigestItem, NormalizedArticle, RawArticle
from app.pipeline.dedupe import deduplicate_articles
from app.pipeline.draft import build_digest_draft
from app.pipeline.fetch import normalize_articles
from app.pipeline.filter import filter_articles
from app.pipeline.publish import publish_digest
from app.pipeline.score import score_articles
from app.pipeline.time_filter import normalize_time_strategies
from app.render.html_renderer import render_digest_html
from app.sources.registry import build_source_adapters
from app.storage.state import StateStore


def _format_published_at(value: object) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return ""


def _serialize_article(item: RawArticle | NormalizedArticle | DigestItem) -> dict[str, Any]:
    return {
        "title": item.title,
        "source": item.source,
        "url": item.url,
        "summary": getattr(item, "summary", ""),
        "score": getattr(item, "score", None),
        "tags": list(getattr(item, "tags", [])),
        "published_at": _format_published_at(getattr(item, "published_at", None)),
    }


def run_digest(
    digest_date: str | None = None,
    selected_sources: list[str] | None = None,
    filter_strategy: str = "standard",
    time_strategies: list[str] | None = None,
    dedupe_strategy: str = "standard",
) -> dict[str, object]:
    config = AppConfig()
    config.ensure_directories()
    ctx = build_digest_context(date.fromisoformat(digest_date) if digest_date else None)
    store = StateStore(config.data_dir / "state.db", Path("app/storage/schema.sql"))
    resolved_time_strategies = normalize_time_strategies(time_strategies)

    raw_articles = []
    for adapter in build_source_adapters(config, selected_sources=selected_sources):
        raw_articles.extend(adapter.fetch(ctx["source_day_compact"]))
    raw_articles.sort(key=lambda article: article.published_at or datetime.min, reverse=True)

    normalized = normalize_articles(raw_articles)
    filtered = filter_articles(
        normalized,
        strategy=filter_strategy,
        time_strategies=resolved_time_strategies,
        source_date=ctx["source_date"],
        digest_date=ctx["digest_date"],
        window_start=config.window_start,
        window_end=config.window_end,
    )
    scored = score_articles(filtered)
    deduped = deduplicate_articles(scored, strategy=dedupe_strategy)
    fresh_articles = [
        article
        for article in deduped
        if not store.is_seen(article.dedupe_key, digest_date=ctx["digest_date"])
    ]
    chosen = sorted(fresh_articles, key=lambda item: item.score, reverse=True)[: config.max_items_per_digest]

    draft = build_digest_draft(
        chosen,
        digest_date=ctx["digest_date"],
        window_label=ctx["window_label"],
        max_items=config.max_items_per_digest,
    )
    html = render_digest_html(Path("app/templates"), draft)
    draft.html = html

    html_path = config.output_dir / f"{ctx['digest_date']}-morning-digest.html"
    json_path = config.output_dir / f"{ctx['digest_date']}-morning-digest.json"
    html_path.write_text(html, encoding="utf-8")
    store.save_draft(draft, html_path, json_path)
    if chosen:
        store.mark_seen(chosen, digest_date=ctx["digest_date"])

    publish_status, publish_message = publish_digest(config, draft, html)
    store.mark_publish_result(
        draft.digest_date,
        config.publish_mode,
        publish_status,
        publish_message,
    )
    return {
        "digest_date": draft.digest_date,
        "source_date": ctx["source_date"],
        "selected_sources": selected_sources or [adapter.source_name for adapter in build_source_adapters(config)],
        "filter_strategy": filter_strategy,
        "time_strategies": resolved_time_strategies,
        "dedupe_strategy": dedupe_strategy,
        "raw_count": len(raw_articles),
        "filtered_count": len(filtered),
        "selected_count": len(chosen),
        "html_path": str(html_path),
        "json_path": str(json_path),
        "html_url": f"/artifacts/{html_path.as_posix()}",
        "json_url": f"/artifacts/{json_path.as_posix()}",
        "publish_status": publish_status,
        "publish_message": publish_message,
        "stages": {
            "raw_articles": [_serialize_article(item) for item in raw_articles],
            "filtered_articles": [_serialize_article(item) for item in filtered],
            "deduped_articles": [_serialize_article(item) for item in deduped],
            "chosen_articles": [_serialize_article(item) for item in chosen],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate morning digest from last evening news.")
    parser.add_argument("command", choices=["digest"])
    parser.add_argument("--digest-date", dest="digest_date")
    parser.add_argument("--time-strategy", dest="time_strategies", action="append")
    args = parser.parse_args()

    if args.command == "digest":
        result = run_digest(digest_date=args.digest_date, time_strategies=args.time_strategies)
        for key, value in result.items():
            print(f"{key}={value}")


if __name__ == "__main__":
    main()
