"""The refinement loop itself."""

from __future__ import annotations

import time
from collections.abc import Callable

from criticloop.critics import Critic, evaluate
from criticloop.types import Draft, Round, Trace

Reviser = Callable[[Draft, tuple[str, ...]], Draft]


def refine(
    initial: Draft,
    critics: list[Critic],
    reviser: Reviser,
    max_rounds: int = 3,
    target: float = 1.0,
) -> Trace:
    """Evaluate, revise, repeat — stopping on the target score or the round cap.

    The trace always contains at least one round, so callers can inspect what the
    critics thought even when the very first draft already passed.
    """

    if max_rounds < 1:
        raise ValueError("max_rounds must be at least 1")

    draft = initial
    trace = Trace(target=target, max_rounds=max_rounds)
    for index in range(max_rounds):
        started = time.perf_counter()
        verdict = evaluate(draft.text, critics)
        trace.rounds.append(
            Round(
                index=index + 1,
                draft=draft,
                verdict=verdict,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )
        if verdict.score >= target or index == max_rounds - 1:
            break
        draft = reviser(draft, verdict.issues)
    return trace
