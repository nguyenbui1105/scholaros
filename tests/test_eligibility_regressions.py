"""Regression tests for hardened evidence-aware eligibility (test-first)."""

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_eligibility import BASE, CLAIM, RULE_CLAIMS, SOURCE_TEXT, STUDENT, TODAY

from scholaros.eligibility import _items, allowed_hosts, assess_eligibility, authority_check
from scholaros.models import Decision


def with_quote(field: str, quote: str) -> object:
    text = SOURCE_TEXT
    old_quote = RULE_CLAIMS[field].quote
    text = text.replace(old_quote, quote)
    digest = sha256(text.encode("utf-8")).hexdigest()
    claims = {
        name: replace(claim, content_hash=digest, quote=quote if name == field else claim.quote)
        for name, claim in RULE_CLAIMS.items()
    }
    return replace(
        BASE,
        source_text=text,
        rule_claims=claims,
        international_claim=replace(
            CLAIM, content_hash=digest, quote=quote if field == "visa_status" else CLAIM.quote
        ),
    )


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), -0.1, 4.1])
def test_invalid_student_gpa_never_eligible(bad: float) -> None:
    result = assess_eligibility(replace(STUDENT, gpa=bad), BASE, today=TODAY)
    assert result.decision is Decision.NEEDS_VERIFICATION
    assert any(reason.field == "gpa" and reason.severity == "unknown" for reason in result.reasons)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, 5.0])
def test_invalid_requirement_gpa_never_eligible(bad: float) -> None:
    result = assess_eligibility(STUDENT, replace(BASE, min_gpa=bad), today=TODAY)
    assert result.decision is Decision.NEEDS_VERIFICATION


@pytest.mark.parametrize(
    "quote",
    [
        "F-1 students are not eligible",
        "F-1 students are ineligible",
        "F-1 students are eligible except those with visas",
        "F-1 students are eligible excluding international applicants",
    ],
)
def test_negated_international_quote_fails_closed(quote: str) -> None:
    opportunity = with_quote("visa_status", quote)
    assert assess_eligibility(STUDENT, opportunity, today=TODAY).decision is not Decision.ELIGIBLE


@pytest.mark.parametrize(
    "field,quote",
    [
        ("academic_level", "Undergraduate students are not eligible"),
        ("majors", "CS majors are ineligible"),
        ("school", "PCC students are eligible except applicants with F-1 visas"),
        ("gpa", "Minimum GPA 3.0 excluding F-1 students"),
    ],
)
def test_negated_requirement_quote_fails_closed(field: str, quote: str) -> None:
    opportunity = with_quote(field, quote)
    assert assess_eligibility(STUDENT, opportunity, today=TODAY).decision is not Decision.ELIGIBLE


def test_gpa_number_without_gpa_context_does_not_verify() -> None:
    opportunity = with_quote("gpa", "3.0 students enrolled")
    assert (
        assess_eligibility(STUDENT, opportunity, today=TODAY).decision
        is Decision.NEEDS_VERIFICATION
    )


@pytest.mark.parametrize("visa", ["F1", "f 1", " F-1 ", "f-1"])
def test_equivalent_visa_tokens_cannot_hard_fail(visa: str) -> None:
    result = assess_eligibility(replace(STUDENT, visa_status=visa), BASE, today=TODAY)
    assert result.decision is Decision.ELIGIBLE


@pytest.mark.parametrize("level", ["Undergrad", "UNDERGRADUATE", "bachelor's"])
def test_equivalent_level_tokens_cannot_hard_fail(level: str) -> None:
    result = assess_eligibility(replace(STUDENT, academic_level=level), BASE, today=TODAY)
    assert result.decision is Decision.ELIGIBLE


def test_bare_string_constraint_rejected() -> None:
    with pytest.raises(TypeError):
        _items("F-1")
    with pytest.raises(TypeError):
        assess_eligibility(STUDENT, replace(BASE, eligible_visas="F-1"), today=TODAY)


def test_bare_tld_host_rejected() -> None:
    assert not authority_check("https://gov/")
    assert not authority_check("https://edu/")


def test_allowlist_yaml_normalizes_case_and_leading_dots(tmp_path: Path) -> None:
    config = tmp_path / "domains.yaml"
    config.write_text('domains:\n  - ".EDU"\n  - ".GOV"\n  - "BÜCHER.example"\n', encoding="utf-8")
    hosts = allowed_hosts(config)
    assert "edu" in hosts and "gov" in hosts
    assert "xn--bcher-kva.example" in hosts
    assert authority_check("https://dept.edu/Student", allowlist=hosts)


def test_missing_config_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        allowed_hosts(tmp_path / "missing.yaml")


def test_invalid_yaml_fails_loudly(tmp_path: Path) -> None:
    config = tmp_path / "domains.yaml"
    config.write_text("domains: [broken", encoding="utf-8")
    with pytest.raises(ValueError):
        allowed_hosts(config)


def test_textual_date_parsed_in_quote() -> None:
    replacement = with_quote("deadline", "Deadline: November 28, 2026")
    assert assess_eligibility(STUDENT, replacement, today=TODAY).decision is Decision.ELIGIBLE


def test_ambiguous_numeric_date_does_not_verify() -> None:
    replacement = with_quote("deadline", "Deadline: 11/12/2026")
    assert (
        assess_eligibility(STUDENT, replacement, today=TODAY).decision
        is Decision.NEEDS_VERIFICATION
    )


@given(st.sampled_from(["nan", "inf", "-inf"]), st.sampled_from(["F-1", "F1", "f 1"]))
def test_property_nonfinite_gpa_never_eligible(raw: str, visa: str) -> None:
    student = replace(STUDENT, gpa=float(raw), visa_status=visa)
    assert assess_eligibility(student, BASE, today=TODAY).decision is not Decision.ELIGIBLE


@given(
    st.sampled_from(["not eligible", "ineligible", "except", "excluding"]),
    st.sampled_from(["F-1", "F1"]),
)
def test_property_negations_never_eligible(negation: str, visa: str) -> None:
    opportunity = with_quote(
        "visa_status", f"F-1 students are eligible {negation} other applicants"
    )
    student = replace(STUDENT, visa_status=visa)
    assert assess_eligibility(student, opportunity, today=TODAY).decision is not Decision.ELIGIBLE


@given(st.sampled_from(["example.com", "gov", "evil.edu.example.com", "localhost", "unknown.org"]))
def test_property_nonallowlisted_hosts_never_eligible(host: str) -> None:
    modified = replace(BASE, official_url=f"https://{host}/award")
    assert assess_eligibility(STUDENT, modified, today=TODAY).decision is not Decision.ELIGIBLE
