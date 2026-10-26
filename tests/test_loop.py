from __future__ import annotations

import pytest

from criticloop.critics import RequiredTerms
from criticloop.loop import refine
from criticloop.types import Draft, Trace


def reviser_that_fixes(draft: Draft, issues: tuple[str, ...]) -> Draft:
    return Draft(text=draft.text + " cache", version=draft.version + 1)


def reviser_that_does_nothing(draft: Draft, issues: tuple[str, ...]) -> Draft:
    return Draft(text=draft.text, version=draft.version + 1)


def test_loop_converges_after_one_revision() -> None:
    trace = refine(
        Draft(text="a summary"),
        [RequiredTerms(("cache",))],
        reviser_that_fixes,
        max_rounds=3,
    )
    assert trace.converged is True
    assert trace.iterations == 2
    assert trace.final is not None
    assert "cache" in trace.final.text
    assert trace.final.version == 1


def test_loop_stops_at_the_round_cap() -> None:
    trace = refine(
        Draft(text="a summary"),
        [RequiredTerms(("cache",))],
        reviser_that_does_nothing,
        max_rounds=4,
    )
    assert trace.converged is False
    assert trace.iterations == 4
    assert trace.rounds[-1].verdict.score == 0.0


def test_clean_draft_stops_immediately() -> None:
    trace = refine(
        Draft(text="a summary about cache"), [RequiredTerms(("cache",))], reviser_that_fixes
    )
    assert trace.iterations == 1
    assert trace.converged is True


def test_custom_target_score() -> None:
    trace = refine(
        Draft(text="a"),
        [RequiredTerms(("cache",)), RequiredTerms(("slo",), name="second")],
        reviser_that_fixes,
        max_rounds=2,
        target=0.5,
    )
    assert trace.converged is True
    assert trace.iterations == 2
    assert trace.rounds[-1].verdict.score == 0.5


def test_invalid_max_rounds() -> None:
    with pytest.raises(ValueError, match="max_rounds"):
        refine(Draft(text="x"), [], reviser_that_fixes, max_rounds=0)


def test_trace_serialises() -> None:
    trace = refine(Draft(text="x"), [RequiredTerms(("cache",))], reviser_that_fixes)
    payload = trace.as_dict()
    assert payload["iterations"] == 2
    assert payload["converged"] is True
    assert payload["rounds"][0]["score"] == 0.0
    assert isinstance(payload["text"], str)


def test_empty_trace_reports_no_final() -> None:
    empty = Trace()
    assert empty.final is None
    assert empty.converged is False
    assert empty.iterations == 0
