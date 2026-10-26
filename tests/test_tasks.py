from __future__ import annotations

import pytest

from criticloop.tasks import (
    SAMPLE_INCIDENT,
    Incident,
    IncidentError,
    build_summary,
    make_reviser,
    run_incident,
)
from criticloop.types import Draft

WITH_CAUSE = {
    "title": "Checkout latency spike",
    "service": "checkout-api",
    "impact": "12% of requests slower than 3s for 23 minutes.",
    "root_cause": "An unbounded cache in release 1.4.0.",
    "events": [
        {"time": "2026-03-02T09:03:00Z", "note": "Latency alert fired."},
        {"time": "2026-03-02T09:26:00Z", "note": "Latency recovered."},
    ],
}

WITHOUT_CAUSE = {key: value for key, value in WITH_CAUSE.items() if key != "root_cause"}


def test_from_dict_validates_required_fields() -> None:
    with pytest.raises(IncidentError, match="title"):
        Incident.from_dict({"service": "svc", "events": [{"time": "t", "note": "n"}]})
    with pytest.raises(IncidentError, match="service"):
        Incident.from_dict({"title": "t", "events": [{"time": "t", "note": "n"}]})
    with pytest.raises(IncidentError, match="events"):
        Incident.from_dict({"title": "t", "service": "s", "events": []})


def test_malformed_event_is_rejected() -> None:
    with pytest.raises(IncidentError, match="event #1"):
        Incident.from_dict({"title": "t", "service": "s", "events": [{"time": "t"}]})


def test_clock_formats_utc() -> None:
    incident = Incident.from_dict(WITH_CAUSE)
    assert incident.clock("2026-03-02T09:03:00Z") == "09:03 UTC"
    assert incident.clock("not-a-time") == "not-a-time"


def test_summary_includes_all_sections_when_data_present() -> None:
    summary = build_summary(Incident.from_dict(WITH_CAUSE))
    assert "## Timeline" in summary
    assert "## Impact" in summary
    assert "## Root cause" in summary
    assert "09:03 UTC" in summary


def test_summary_omits_unknown_root_cause() -> None:
    summary = build_summary(Incident.from_dict(WITHOUT_CAUSE))
    assert "## Root cause" not in summary


def test_loop_adds_honest_placeholder_for_missing_root_cause() -> None:
    trace = run_incident(Incident.from_dict(WITHOUT_CAUSE), max_rounds=3)
    assert trace.converged is True
    assert trace.iterations > 1
    assert trace.final is not None
    assert "## Root cause" in trace.final.text
    assert "Not yet confirmed" in trace.final.text


def test_complete_incident_converges_in_one_round() -> None:
    trace = run_incident(Incident.from_dict(SAMPLE_INCIDENT))
    assert trace.converged is True
    assert trace.iterations == 1


def test_reviser_trims_next_steps_to_word_limit() -> None:
    incident = Incident.from_dict(WITH_CAUSE)
    revise = make_reviser(incident, word_limit=25)
    draft = Draft(
        text=(
            "## Timeline\n\n- 09:03 UTC — alert.\n- 09:26 UTC — recovered.\n\n"
            "## Impact\n\nSome impact.\n\n## Root cause\n\nA cache.\n\n## Next steps\n\n"
            "- Follow up with the team about the cache change.\n"
            "- Add a regression test for the cache limit.\n"
            "- Link the postmortem in the release notes for this version.\n"
        )
    )
    revised = revise(draft, ("too long",))
    assert len(revised.text.split()) < len(draft.text.split())
    assert revised.version == draft.version + 1
