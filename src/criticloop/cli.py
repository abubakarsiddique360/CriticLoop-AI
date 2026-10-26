"""Command-line interface for CriticLoop."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from criticloop import __version__
from criticloop.critics import default_critics
from criticloop.tasks import (
    SAMPLE_INCIDENT,
    Incident,
    IncidentError,
    incident_critics,
    run_incident,
)


def _run(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    incident = Incident.from_dict(data)
    trace = run_incident(incident, max_rounds=args.max_rounds, word_limit=args.word_limit)
    if args.json:
        print(json.dumps(trace.as_dict(), indent=2))
        return 0
    print(f"Incident : {incident.title} ({incident.service})")
    print(f"Converged: {trace.converged} after {trace.iterations} round(s)")
    print()
    for round_ in trace.rounds:
        print(f"round {round_.index}: score {round_.verdict.score:.2f}")
        for issue in round_.verdict.issues:
            print(f"  - {issue}")
    print()
    print(trace.final.text if trace.final else "")
    return 0


def _demo(args: argparse.Namespace) -> int:
    trace = run_incident(Incident.from_dict(SAMPLE_INCIDENT), max_rounds=args.max_rounds)
    print(f"Converged: {trace.converged} after {trace.iterations} round(s)")
    print()
    print(trace.final.text if trace.final else "")
    return 0


def _critics(args: argparse.Namespace) -> int:
    print("incident task critics:")
    for critic in incident_critics():
        print(f"  {critic.name}")
    print("library defaults:")
    for critic in default_critics():
        print(f"  {critic.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="criticloop",
        description="Refine a draft until deterministic critics are satisfied.",
    )
    parser.add_argument("--version", action="version", version=f"criticloop {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="summarise an incident JSON file through the loop")
    run.add_argument("file")
    run.add_argument("--max-rounds", type=int, default=3)
    run.add_argument("--word-limit", type=int, default=160)
    run.add_argument("--json", action="store_true")
    run.set_defaults(func=_run)

    demo = sub.add_parser("demo", help="run the built-in sample incident")
    demo.add_argument("--max-rounds", type=int, default=3)
    demo.set_defaults(func=_demo)

    critics = sub.add_parser("critics", help="list the critics in use")
    critics.set_defaults(func=_critics)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (IncidentError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
