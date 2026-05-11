CREATE TABLE IF NOT EXISTS article_seen (
    dedupe_key TEXT PRIMARY KEY,
    digest_date TEXT NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS draft_history (
    digest_date TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    intro TEXT NOT NULL,
    html_path TEXT NOT NULL,
    json_path TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publish_history (
    digest_date TEXT PRIMARY KEY,
    publish_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
