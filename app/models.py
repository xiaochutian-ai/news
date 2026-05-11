from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class RawArticle:
    source: str
    source_id: str
    title: str
    url: str
    published_at: datetime | None
    summary: str = ""
    content: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class NormalizedArticle:
    source: str
    source_id: str
    title: str
    url: str
    published_at: datetime
    summary: str
    content: str
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    reason_codes: list[str] = field(default_factory=list)
    dedupe_key: str = ""


@dataclass(slots=True)
class DigestItem:
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    score: float
    reason: str


@dataclass(slots=True)
class DigestDraft:
    digest_date: str
    title: str
    intro: str
    window_label: str
    items: list[DigestItem]
    generated_at: datetime
    html: str = ""
