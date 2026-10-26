"""An example task: turn a structured incident timeline into a summary.

The solver is intentionally incomplete — it omits a section it cannot fill. The
critics notice, the reviser adds an honest placeholder, and the loop converges.
That is the behaviour worth demonstrating: correction without inventing facts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from criticloop.critics import (
    Critic,
    ForbiddenTerms,
    MaxWords,
    NoRepeatedSentences,
    RequiredSections,
    RequiredTerms,
)
from criticloop.loop import Reviser, refine
from criticloop.types import Draft, Trace

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")


class IncidentError(ValueError):
    """Raised when incident data is missing or malformed."""


@dataclass(frozen=True)
class Incident:
    title: str
    service: str
    events: tuple[dict, ...]
    root_cause: str | None = None
    impact: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Incident:
        if not isinstance(data, dict):
            raise IncidentError("incident root must be an object")
        title = str(data.get("title", "")).strip()
        service = str(data.get("service", "")).strip()
        raw_events = data.get("events")
        if not title:
            raise IncidentError("'title' is required")
        if not service:
            raise IncidentError("'service' is required")
        if not isinstance(raw_events, list) or not raw_events:
            raise IncidentError("'events' must be a non-empty list")
        events = []
        for index, event in enumerate(raw_events, start=1):
            if not isinstance(event, dict) or "time" not in event or "note" not in event:
                raise IncidentError(f"event #{index} needs 'time' and 'note'")
            events.append({"time": str(event["time"]), "note": str(event["note"])})
        return cls(
            title=title,
            service=service,
            events=tuple(events),
            root_cause=(str(data["root_cause"]).strip() if data.get("root_cause") else None),
            impact=(str(data["impact"]).strip() if data.get("impact") else None),
        )

    def clock(self, stamp: str) -> str:
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            return stamp
        return f"{parsed.strftime('%H:%M')} UTC"


def build_summary(incident: Incident) -> str:
    lines = [f"# {incident.title}", "", f"Service: {incident.service}", "", "## Timeline", ""]
    for event in incident.events:
        lines.append(f"- {incident.clock(event['time'])} — {event['note']}")
    lines += [
        "",
        "## Impact",
        "",
        incident.impact or "Impact is still being measured for this incident.",
        "",
    ]
    if incident.root_cause:
        lines += ["## Root cause", "", incident.root_cause, ""]
    lines += [
        "## Next steps",
        "",
        "- Keep the incident open until the root cause is confirmed.",
        "- Add a regression test that reproduces the failure.",
    ]
    return "\n".join(lines).strip() + "\n"


def incident_critics(word_limit: int = 160) -> list[Critic]:
    return [
        RequiredSections(("Timeline", "Impact", "Root cause", "Next steps")),
        RequiredTerms(("UTC",)),
        ForbiddenTerms(("probably", "i think", "might be")),
        MaxWords(word_limit),
        NoRepeatedSentences(),
    ]


def make_reviser(incident: Incident, word_limit: int = 160) -> Reviser:
    def revise(draft: Draft, issues: tuple[str, ...]) -> Draft:
        text = draft.text
        if any("Root cause" in issue for issue in issues) and "## Root cause" not in text:
            placeholder = (
                "## Root cause\n\n"
                "Not yet confirmed. The incident stays open until the cause is proven by evidence.\n"
            )
            if "## Next steps" in text:
                text = text.replace("## Next steps", placeholder + "\n## Next steps", 1)
            else:
                text = f"{text.rstrip()}\n\n{placeholder}"
        if any("Impact" in issue for issue in issues) and "## Impact" not in text:
            text = text.replace(
                "## Next steps", "## Impact\n\nScope under assessment.\n\n## Next steps", 1
            )

        while len(_WORD_RE.findall(text)) > word_limit:
            bullets = [line for line in text.splitlines() if line.startswith("- ")]
            if len(bullets) <= 1:
                break
            text = text.replace(bullets[-1] + "\n", "", 1)

        seen: set[str] = set()
        kept: list[str] = []
        for line in text.splitlines():
            key = " ".join(line.lower().split())
            if len(key) > 40 and key in seen:
                continue
            if len(key) > 40:
                seen.add(key)
            kept.append(line)
        return Draft(text="\n".join(kept), version=draft.version + 1, metadata=draft.metadata)

    return revise


def run_incident(incident: Incident, max_rounds: int = 3, word_limit: int = 160) -> Trace:
    initial = Draft(text=build_summary(incident), version=0, metadata={"service": incident.service})
    return refine(
        initial=initial,
        critics=incident_critics(word_limit),
        reviser=make_reviser(incident, word_limit),
        max_rounds=max_rounds,
    )


SAMPLE_INCIDENT: dict = {
    "title": "Checkout latency spike",
    "service": "checkout-api",
    "impact": "About 12% of checkout requests took longer than three seconds for 23 minutes.",
    "root_cause": "Release 1.4.0 shipped an unbounded in-process cache.",
    "events": [
        {"time": "2026-03-02T09:03:00Z", "note": "Latency alert fired: p95 at 4.2 seconds."},
        {"time": "2026-03-02T09:11:00Z", "note": "Release 1.4.0 rolled back."},
        {"time": "2026-03-02T09:26:00Z", "note": "p95 recovered to 320 milliseconds."},
    ],
}
