from datetime import datetime

from app.models import DigestDraft, DigestItem, NormalizedArticle
from app.pipeline.draft import build_digest_draft


def _article(title: str, score: float) -> NormalizedArticle:
    return NormalizedArticle(
        source="cctv",
        source_id=title,
        title=title,
        url=f"https://example.com/{title}",
        published_at=datetime(2026, 5, 10, 21, 30, 0),
        summary="围绕群众生活的重点变化。",
        content="围绕群众生活的重点变化，带来直接影响。",
        tags=["民生"],
        score=score,
        reason_codes=["topic:民生", "freshness:recent"],
    )


def test_build_digest_draft_limits_items_and_creates_intro() -> None:
    draft = build_digest_draft(
        [
            _article("政策一", 95),
            _article("政策二", 94),
            _article("政策三", 93),
            _article("政策四", 92),
            _article("政策五", 91),
            _article("政策六", 90),
            _article("政策七", 89),
            _article("政策八", 88),
        ],
        digest_date="2026-05-11",
        window_label="2026-05-10 19:30-22:30",
        max_items=7,
    )

    assert isinstance(draft, DigestDraft)
    assert len(draft.items) == 7
    assert "晚间民生热点" in draft.intro
    assert draft.items[0].title == "政策一"


def test_build_digest_draft_uses_article_summary_and_reason_codes() -> None:
    draft = build_digest_draft(
        [_article("多地加力稳就业", 96)],
        digest_date="2026-05-11",
        window_label="2026-05-10 19:30-22:30",
        max_items=7,
    )

    first_item: DigestItem = draft.items[0]
    assert "围绕群众生活的重点变化" in first_item.summary
    assert "topic:民生" in first_item.reason
