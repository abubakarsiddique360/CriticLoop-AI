"""Core data structures for the refinement loop."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Draft:
    text: str
    version: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Verdict:
    issues: tuple[str, ...] = ()
    passed: int = 0
    total: int = 0

    @property
    def score(self) -> float:
        return round(self.passed / self.total, 3) if self.total else 1.0

    @property
    def ok(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class Round:
    index: int
    draft: Draft
    verdict: Verdict
    duration_ms: int = 0

    def as_dict(self) -> dict:
        return {
            "round": self.index,
            "version": self.draft.version,
            "score": self.verdict.score,
            "issues": list(self.verdict.issues),
            "duration_ms": self.duration_ms,
        }


@dataclass
class Trace:
    rounds: list[Round] = field(default_factory=list)
    target: float = 1.0
    max_rounds: int = 3

    @property
    def final(self) -> Draft | None:
        return self.rounds[-1].draft if self.rounds else None

    @property
    def converged(self) -> bool:
        return bool(self.rounds) and self.rounds[-1].verdict.score >= self.target

    @property
    def iterations(self) -> int:
        return len(self.rounds)

    def as_dict(self) -> dict:
        return {
            "converged": self.converged,
            "iterations": self.iterations,
            "target": self.target,
            "max_rounds": self.max_rounds,
            "final_score": self.rounds[-1].verdict.score if self.rounds else 0.0,
            "text": self.final.text if self.final else "",
            "rounds": [round_.as_dict() for round_ in self.rounds],
        }
