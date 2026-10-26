"""Deterministic critics.

A critic is a named function from text to a list of human-readable issues. They
are cheap, explainable and repeatable — which is the whole point: the loop's stop
condition must not depend on a model's opinion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from criticloop.types import Verdict

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class Critic(Protocol):
    name: str

    def check(self, text: str) -> list[str]: ...


@dataclass(frozen=True)
class RequiredTerms:
    terms: tuple[str, ...]
    name: str = "required-terms"

    def check(self, text: str) -> list[str]:
        lowered = text.lower()
        return [
            f"missing required term: {term}" for term in self.terms if term.lower() not in lowered
        ]


@dataclass(frozen=True)
class ForbiddenTerms:
    terms: tuple[str, ...]
    name: str = "forbidden-terms"

    def check(self, text: str) -> list[str]:
        lowered = text.lower()
        return [f"forbidden hedge: {term}" for term in self.terms if term.lower() in lowered]


@dataclass(frozen=True)
class RequiredSections:
    headings: tuple[str, ...]
    name: str = "required-sections"

    def check(self, text: str) -> list[str]:
        found = {
            match.group(1).strip().lower()
            for match in re.finditer(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
        }
        return [
            f"missing section: {heading}"
            for heading in self.headings
            if heading.lower() not in found
        ]


@dataclass(frozen=True)
class MaxWords:
    limit: int
    name: str = "max-words"

    def check(self, text: str) -> list[str]:
        count = len(_WORD_RE.findall(text))
        return [f"too long: {count} words (limit {self.limit})"] if count > self.limit else []


@dataclass(frozen=True)
class MaxSentenceWords:
    limit: int
    name: str = "max-sentence-words"

    def check(self, text: str) -> list[str]:
        issues: list[str] = []
        for sentence in _SENTENCE_RE.split(text):
            count = len(_WORD_RE.findall(sentence))
            if count > self.limit:
                issues.append(f"sentence too long: {count} words (limit {self.limit})")
        return issues


@dataclass(frozen=True)
class NoRepeatedSentences:
    name: str = "no-repeated-sentences"

    def check(self, text: str) -> list[str]:
        seen: set[str] = set()
        issues: list[str] = []
        for sentence in _SENTENCE_RE.split(text):
            normalized = " ".join(sentence.lower().split())
            if len(normalized) < 20:
                continue
            if normalized in seen:
                issues.append(f"duplicate sentence: {sentence.strip()[:60]}...")
            seen.add(normalized)
        return issues


def default_critics() -> list[Critic]:
    return [
        RequiredSections(("Timeline", "Impact", "Root cause", "Next steps")),
        MaxWords(160),
        ForbiddenTerms(("probably", "i think", "might be")),
        NoRepeatedSentences(),
    ]


def evaluate(text: str, critics: list[Critic]) -> Verdict:
    issues: list[str] = []
    passed = 0
    for critic in critics:
        found = critic.check(text)
        if found:
            issues.extend(f"[{critic.name}] {issue}" for issue in found)
        else:
            passed += 1
    return Verdict(issues=tuple(issues), passed=passed, total=len(critics))
