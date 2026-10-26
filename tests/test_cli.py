from __future__ import annotations

import json
from pathlib import Path

from criticloop.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_run_complete_incident(capsys) -> None:
    assert main(["run", str(EXAMPLES / "incident.json")]) == 0
    out = capsys.readouterr().out
    assert "Converged: True" in out
    assert "# Checkout latency spike" in out


def test_run_incomplete_incident_self_corrects(capsys) -> None:
    assert main(["run", str(EXAMPLES / "incident-missing-root-cause.json")]) == 0
    out = capsys.readouterr().out
    assert "Converged: True" in out
    assert "## Root cause" in out


def test_json_output(capsys) -> None:
    assert main(["run", str(EXAMPLES / "incident.json"), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["converged"] is True
    assert payload["iterations"] >= 1
    assert payload["rounds"]


def test_max_rounds_can_prevent_convergence(capsys) -> None:
    assert (
        main(["run", str(EXAMPLES / "incident-missing-root-cause.json"), "--max-rounds", "1"]) == 0
    )
    payload = capsys.readouterr().out
    assert "Converged: False" in payload


def test_missing_file_exits_two(tmp_path, capsys) -> None:
    assert main(["run", str(tmp_path / "nope.json")]) == 2
    assert "error" in capsys.readouterr().err


def test_invalid_incident_exits_two(tmp_path, capsys) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text('{"title": "x"}', encoding="utf-8")
    assert main(["run", str(broken)]) == 2
    assert "service" in capsys.readouterr().err


def test_demo_runs(capsys) -> None:
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "Converged: True" in out
    assert "checkout-api" in out


def test_critics_listing(capsys) -> None:
    assert main(["critics"]) == 0
    out = capsys.readouterr().out
    assert "required-sections" in out
    assert "max-words" in out
