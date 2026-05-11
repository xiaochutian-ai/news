from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app.models import DigestDraft, NormalizedArticle


class StateStore:
    def __init__(self, db_path: Path, schema_path: Path) -> None:
        self.db_path = db_path
        self.schema_path = schema_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(self.schema_path.read_text(encoding="utf-8"))
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(article_seen)").fetchall()
            }
            if columns and "digest_date" not in columns:
                conn.execute("DROP TABLE article_seen")
                conn.execute(
                    """
                    CREATE TABLE article_seen (
                        dedupe_key TEXT PRIMARY KEY,
                        digest_date TEXT NOT NULL,
                        source TEXT NOT NULL,
                        title TEXT NOT NULL,
                        url TEXT NOT NULL,
                        first_seen_at TEXT NOT NULL
                    )
                    """
                )
            conn.commit()

    def is_seen(self, dedupe_key: str, digest_date: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM article_seen WHERE dedupe_key = ? AND digest_date != ?",
                (dedupe_key, digest_date),
            ).fetchone()
        return row is not None

    def mark_seen(self, articles: list[NormalizedArticle], digest_date: str) -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO article_seen(dedupe_key, digest_date, source, title, url, first_seen_at) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        article.dedupe_key,
                        digest_date,
                        article.source,
                        article.title,
                        article.url,
                        now,
                    )
                    for article in articles
                ],
            )
            conn.commit()

    def save_draft(self, draft: DigestDraft, html_path: Path, json_path: Path) -> None:
        payload = {
            "digest_date": draft.digest_date,
            "title": draft.title,
            "intro": draft.intro,
            "window_label": draft.window_label,
            "generated_at": draft.generated_at.isoformat(),
            "items": [
                {
                    "title": item.title,
                    "summary": item.summary,
                    "source": item.source,
                    "url": item.url,
                    "published_at": item.published_at.isoformat(),
                    "score": item.score,
                    "reason": item.reason,
                }
                for item in draft.items
            ],
        }
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO draft_history(digest_date, title, intro, html_path, json_path, generated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    draft.digest_date,
                    draft.title,
                    draft.intro,
                    str(html_path),
                    str(json_path),
                    draft.generated_at.isoformat(),
                ),
            )
            conn.commit()

    def mark_publish_result(
        self,
        digest_date: str,
        publish_mode: str,
        status: str,
        message: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO publish_history(digest_date, publish_mode, status, message, updated_at) VALUES (?, ?, ?, ?, ?)",
                (
                    digest_date,
                    publish_mode,
                    status,
                    message,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_dashboard_preferences(self) -> dict[str, object] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT selected_sources_json, filter_strategy, blocked_keywords_text, time_strategies_json, dedupe_strategy
                FROM dashboard_preferences
                WHERE preference_key = ?
                """,
                ("default",),
            ).fetchone()
        if row is None:
            return None
        return {
            "selected_sources": json.loads(row["selected_sources_json"]),
            "filter_strategy": row["filter_strategy"],
            "blocked_keywords_text": row["blocked_keywords_text"],
            "time_strategies": json.loads(row["time_strategies_json"]),
            "dedupe_strategy": row["dedupe_strategy"],
        }

    def save_dashboard_preferences(
        self,
        *,
        selected_sources: list[str],
        filter_strategy: str,
        blocked_keywords_text: str,
        time_strategies: list[str],
        dedupe_strategy: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO dashboard_preferences(
                    preference_key,
                    selected_sources_json,
                    filter_strategy,
                    blocked_keywords_text,
                    time_strategies_json,
                    dedupe_strategy,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "default",
                    json.dumps(selected_sources, ensure_ascii=False),
                    filter_strategy,
                    blocked_keywords_text,
                    json.dumps(time_strategies, ensure_ascii=False),
                    dedupe_strategy,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
