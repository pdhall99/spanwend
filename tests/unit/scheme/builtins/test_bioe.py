"""Tests for semantics specific to the BIOE/BIEO built-in."""

import pytest

from spanwend import (
    DiagnosticCode,
    InvalidTagSequenceError,
    Span,
    check_conformance,
    convert,
    decode,
    encode,
)


def test_bioe_encodes_singleton_and_multi_token_spans() -> None:
    spans = [Span(0, 1, "PER"), Span(2, 4, "ORG"), Span(5, 8, "LOC")]

    tags = encode(spans, length=8, scheme="bioe")

    assert tags == (
        "B-PER",
        "O",
        "B-ORG",
        "E-ORG",
        "O",
        "B-LOC",
        "I-LOC",
        "E-LOC",
    )
    assert decode(tags, scheme="bioe") == tuple(spans)


@pytest.mark.parametrize(
    ("tags", "code", "index"),
    [
        (["I-PER"], DiagnosticCode.INVALID_START, 0),
        (["E-PER"], DiagnosticCode.INVALID_START, 0),
        (["B-PER", "I-ORG"], DiagnosticCode.LABEL_MISMATCH, 1),
        (["B-PER", "E-ORG"], DiagnosticCode.LABEL_MISMATCH, 1),
        (["B-PER", "I-PER", "O"], DiagnosticCode.INVALID_TRANSITION, 2),
        (["B-PER", "I-PER"], DiagnosticCode.UNTERMINATED_SPAN, 1),
        (["S-PER"], DiagnosticCode.UNSUPPORTED_MARKER, 0),
    ],
)
def test_bioe_rejects_invalid_sequences(
    tags: list[str],
    code: DiagnosticCode,
    index: int,
) -> None:
    result = check_conformance(tags, scheme="bioe")

    assert [diagnostic.code for diagnostic in result.diagnostics] == [code]
    assert result.diagnostics[0].index == index
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="bioe")
    assert exc_info.value.diagnostics == result.diagnostics


def test_bioe_uses_marker_lookahead_before_label_matching() -> None:
    result = check_conformance(["B-PER", "I-ORG"], scheme="bioe")

    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        DiagnosticCode.LABEL_MISMATCH
    ]


def test_bieo_alias_matches_bioe() -> None:
    spans = [Span(0, 1, "PER"), Span(1, 4, "ORG")]

    expected = encode(spans, length=4, scheme="bioe")

    assert encode(spans, length=4, scheme="bieo") == expected
    assert decode(expected, scheme="bieo") == tuple(spans)
    assert check_conformance(expected, scheme="bieo").conformant


def test_bioe_converts_through_canonical_spans() -> None:
    tags = ("B-PER", "O", "B-ORG", "E-ORG")

    converted = convert(tags, source="bioe", target="bioes")

    assert converted == ("S-PER", "O", "B-ORG", "E-ORG")
    assert convert(converted, source="bioes", target="bioe") == tags
