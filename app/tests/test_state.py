from __future__ import annotations

from datetime import datetime

from app.models import NormalizedArticle
from app.storage.state import StateStore


def test_dashboard_preferences_can_be_saved_and_loaded(tmp_path) -> None:
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        """
        CREATE TABLE IF NOT EXISTS article_seen (
            dedupe_key TEXT PRIMARY KEY,
            digest_date TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            first_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS dashboard_preferences (
            preference_key TEXT PRIMARY KEY,
            selected_sources_json TEXT NOT NULL,
            filter_strategy TEXT NOT NULL,
            blocked_keywords_text TEXT NOT NULL,
            time_strategies_json TEXT NOT NULL,
            dedupe_strategy TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        encoding="utf-8",
    )
    store = StateStore(tmp_path / "state.db", schema_path)

    store.save_dashboard_preferences(
        selected_sources=["xinhua", "cctv"],
        filter_strategy="strict",
        blocked_keywords_text="习近平，李强",
        time_strategies=["source_day", "source_window"],
        dedupe_strategy="aggressive",
    )

    assert store.get_dashboard_preferences() == {
        "selected_sources": ["xinhua", "cctv"],
        "filter_strategy": "strict",
        "blocked_keywords_text": "习近平，李强",
        "time_strategies": ["source_day", "source_window"],
        "dedupe_strategy": "aggressive",
    }


def test_is_seen_does_not_hide_same_digest_rerun(tmp_path) -> None:
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        """
        CREATE TABLE IF NOT EXISTS article_seen (
            dedupe_key TEXT PRIMARY KEY,
            digest_date TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            first_seen_at TEXT NOT NULL
        );
        """,
        encoding="utf-8",
    )
    store = StateStore(tmp_path / "state.db", schema_path)
    article = NormalizedArticle(
        source="people_daily",
        source_id="1",
        title="各地办理“全国通办”68.2万件",
        url="https://example.com/1",
        published_at=datetime(2026, 5, 10, 21, 0, 0),
        summary="summary",
        content="content",
        tags=["公共服务"],
        dedupe_key="same-key",
    )

    store.mark_seen([article], digest_date="2026-05-11")

    assert store.is_seen("same-key", digest_date="2026-05-11") is False
    assert store.is_seen("same-key", digest_date="2026-05-12") is True
