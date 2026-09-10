"""Known-answer conformance and regression fixtures."""

import pytest

from spanwend import (
    DEFAULT_SYNTAX,
    DiagnosticCode,
    InvalidTagSequenceError,
    Span,
    TagSyntax,
    UnrepresentableError,
    check_conformance,
    check_representability,
    decode,
    encode,
)
from spanwend._scheme.builtins.registry import _SchemeKey
from tests.conformance._conformance import reference_encode


def test_bio_initial_i_is_strictly_nonconformant() -> None:
    tags = ["I-PER", "I-PER"]
    result = check_conformance(tags, scheme="bio")

    assert not result.conformant
    assert result.diagnostics[0].code is DiagnosticCode.INVALID_START
    with pytest.raises(InvalidTagSequenceError):
        decode(tags, scheme="bio")


def test_io_adjacent_same_label_loss_is_explicit() -> None:
    spans = [Span(0, 1, "PER"), Span(1, 2, "PER")]

    assert not check_representability(spans, length=2, scheme="io").representable
    with pytest.raises(UnrepresentableError):
        encode(spans, length=2, scheme="io")


def test_contextual_iob1_known_answer_is_fixture_based() -> None:
    spans = [Span(0, 1, "PER"), Span(1, 3, "PER")]
    expected = ("I-PER", "B-PER", "I-PER")

    assert reference_encode(spans, length=3, scheme="iob1") == expected
    assert encode(spans, length=3, scheme="iob1") == expected


def test_contextual_ioe1_known_answer_is_fixture_based() -> None:
    spans = [Span(0, 2, "PER"), Span(2, 3, "PER")]
    expected = ("I-PER", "E-PER", "I-PER")

    assert reference_encode(spans, length=3, scheme="ioe1") == expected
    assert encode(spans, length=3, scheme="ioe1") == expected


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        ("bioe", ("B-PER", "B-PER", "E-PER")),
        ("bios", ("S-PER", "B-PER", "I-PER")),
        ("ioe2", ("E-PER", "I-PER", "E-PER")),
        ("ioes", ("S-PER", "I-PER", "E-PER")),
        ("bmes", ("S-PER", "B-PER", "E-PER")),
        ("bmeow", ("W-PER", "B-PER", "E-PER")),
    ],
)
def test_expanded_scheme_known_answers_are_fixture_based(
    scheme: _SchemeKey,
    expected: tuple[str, ...],
) -> None:
    spans = [Span(0, 1, "PER"), Span(1, 3, "PER")]

    assert reference_encode(spans, length=3, scheme=scheme) == expected
    assert encode(spans, length=3, scheme=scheme) == expected


@pytest.mark.parametrize(
    "spans",
    [
        [Span(0, 1, "PER"), Span(0, 1, "PER")],
        [Span(0, 2, "PER"), Span(1, 3, "ORG")],
        [Span(0, 4, "ORG"), Span(1, 2, "PER")],
    ],
)
def test_duplicate_overlap_and_nesting_regressions(spans: list[Span]) -> None:
    assert not check_representability(spans, length=4, scheme="bio").representable
    with pytest.raises(UnrepresentableError):
        encode(spans, length=4, scheme="bio")


def test_suffix_syntax_round_trip_regression() -> None:
    syntax = TagSyntax(placement="suffix")
    spans = [Span(0, 2, "PER")]

    assert encode(spans, length=2, scheme="bio", syntax=syntax) == (
        "PER-B",
        "PER-I",
    )
    assert decode(["PER-B", "PER-I"], scheme="bio", syntax=syntax) == tuple(spans)


def test_label_containing_separator_round_trips() -> None:
    spans = [Span(0, 2, "WORK-OF-ART")]

    tags = encode(spans, length=2, scheme="bio")
    assert tags == ("B-WORK-OF-ART", "I-WORK-OF-ART")
    assert decode(tags, scheme="bio") == tuple(spans)


def test_label_equal_to_outside_marker_is_not_outside() -> None:
    spans = [Span(0, 1, "O")]

    tags = encode(spans, length=2, scheme="bio", syntax=DEFAULT_SYNTAX)
    assert tags == ("B-O", "O")
    assert decode(tags, scheme="bio") == tuple(spans)
