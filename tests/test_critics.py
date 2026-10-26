from __future__ import annotations

from criticloop.critics import (
    ForbiddenTerms,
    MaxSentenceWords,
    MaxWords,
    NoRepeatedSentences,
    RequiredSections,
    RequiredTerms,
    default_critics,
    evaluate,
)

GOOD = """# Summary

## Timeline

- 09:03 UTC — alert fired.
- 09:11 UTC — rollback started.

## Impact

Twelve percent of requests were slow.

## Root cause

An unbounded cache.

## Next steps

- Add a regression test.
"""


def test_required_terms_reports_each_missing_term() -> None:
    critic = RequiredTerms(("UTC", "regression"))
    assert critic.check(GOOD) == []
    assert critic.check("no timestamps here") == [
        "missing required term: UTC",
        "missing required term: regression",
    ]


def test_forbidden_terms_flags_hedges() -> None:
    critic = ForbiddenTerms(("probably", "i think"))
    issues = critic.check("It was probably a cache issue.")
    assert issues == ["forbidden hedge: probably"]
    assert critic.check("The rollback fixed it.") == []


def test_required_sections_detects_headings() -> None:
    critic = RequiredSections(("Timeline", "Root cause"))
    assert critic.check(GOOD) == []
    issues = critic.check("## Timeline\n\nonly this")
    assert issues == ["missing section: Root cause"]


def test_max_words() -> None:
    critic = MaxWords(10)
    assert critic.check("one two three") == []
    assert critic.check(" ".join(["word"] * 12)) == ["too long: 12 words (limit 10)"]


def test_max_sentence_words() -> None:
    critic = MaxSentenceWords(5)
    issues = critic.check("This sentence is far too long to pass. Short one.")
    assert len(issues) == 1
    assert "limit 5" in issues[0]


def test_no_repeated_sentences() -> None:
    critic = NoRepeatedSentences()
    text = (
        "The rollback restored latency within minutes. "
        "The rollback restored latency within minutes."
    )
    assert len(critic.check(text)) == 1
    assert critic.check("One sentence. Another sentence.") == []


def test_evaluate_scores_each_critic() -> None:
    verdict = evaluate("just some words", [RequiredTerms(("cache",)), MaxWords(100)])
    assert verdict.total == 2
    assert verdict.passed == 1
    assert verdict.score == 0.5
    assert verdict.ok is False
    assert verdict.issues[0].startswith("[required-terms]")


def test_evaluate_passes_clean_text() -> None:
    verdict = evaluate(GOOD, [RequiredSections(("Timeline",)), ForbiddenTerms(("probably",))])
    assert verdict.score == 1.0
    assert verdict.ok is True


def test_default_critics_are_named() -> None:
    names = [critic.name for critic in default_critics()]
    assert "required-sections" in names
    assert "max-words" in names
