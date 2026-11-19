from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from scholaros.ingestion import (
    IndexedAward,
    OregonStudentAidConnector,
    PCCFoundationConnector,
    deduplicate,
    extract_candidates,
    fetch_official,
    html_to_text,
    source_is_fresh,
    validate_extracted_quote,
)
from scholaros.records import SourceSnapshot

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_award.html"


def test_html_extraction_quotes_and_scripts() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    text = html_to_text(html)
    assert "ignore previous instructions" not in text
    snapshot = SourceSnapshot.from_text(
        "https://www.pcc.edu/enroll/paying-for-college/scholarships/apply/",
        text,
        datetime(2026, 11, 18, tzinfo=UTC),
    )
    candidates = extract_candidates(snapshot)
    assert {c.field for c in candidates} == {"international", "min_gpa", "deadline"}
    assert all(validate_extracted_quote(c.quote, snapshot) for c in candidates)
    assert not validate_extracted_quote("F-1 students always win", snapshot)


def test_freshness() -> None:
    when = datetime(2026, 11, 18, tzinfo=UTC)
    snapshot = SourceSnapshot.from_text("https://pcc.edu", "test", when)
    assert source_is_fresh(snapshot, when + timedelta(days=90))
    assert not source_is_fresh(snapshot, when + timedelta(days=91))
    assert not source_is_fresh(snapshot, when - timedelta(days=1))


def test_dedup_by_provider_and_cycle() -> None:
    awards = [
        IndexedAward("a", "PCC", "STEM merit scholarship", date(2027, 2, 1)),
        IndexedAward("b", "pcc", " STEM  Merit  Scholarship ", date(2027, 2, 1)),
        IndexedAward("c", "PCC", "STEM merit scholarship", date(2028, 2, 1)),
        IndexedAward("d", "OSAC", "STEM merit scholarship", date(2027, 2, 1)),
    ]
    assert [a.id for a in deduplicate(awards)] == ["a", "c", "d"]


@pytest.mark.parametrize("connector", [PCCFoundationConnector(), OregonStudentAidConnector()])
def test_live_disabled_by_default(connector: object, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Offline cache miss"):
        fetch_official(connector, cache_dir=tmp_path)  # type: ignore[arg-type]
