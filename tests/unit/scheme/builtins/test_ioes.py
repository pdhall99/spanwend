"""Tests for semantics specific to the IOES built-in."""

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


def test_ioes_encodes_singleton_and_multi_token_spans() -> None:
    spans = [Span(0, 1, "PER"), Span(2, 4, "ORG"), Span(5, 8, "LOC")]

    tags = encode(spans, length=8, scheme="ioes")

    assert tags == (
        "S-PER",
        "O",
        "I-ORG",
        "E-ORG",
        "O",
        "I-LOC",
        "I-LOC",
        "E-LOC",
    )
    assert decode(tags, scheme="ioes") == tuple(spans)


@pytest.mark.parametrize(
    ("tags", "code", "index"),
    [
        (["E-PER"], DiagnosticCode.INVALID_START, 0),
        (["I-PER"], DiagnosticCode.UNTERMINATED_SPAN, 0),
        (["I-PER", "O"], DiagnosticCode.INVALID_TRANSITION, 1),
        (["I-PER", "E-ORG"], DiagnosticCode.LABEL_MISMATCH, 1),
        (["B-PER"], DiagnosticCode.UNSUPPORTED_MARKER, 0),
    ],
)
def test_ioes_rejects_invalid_sequences(
    tags: list[str],
    code: DiagnosticCode,
    index: int,
) -> None:
    result = check_conformance(tags, scheme="ioes")

    assert result.diagnostics[0].code is code
    assert result.diagnostics[0].index == index
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="ioes")
    assert exc_info.value.diagnostics == result.diagnostics


def test_ioes_converts_through_canonical_spans() -> None:
    tags = ("S-PER", "O", "I-ORG", "E-ORG")

    converted = convert(tags, source="ioes", target="bioes")

    assert converted == ("S-PER", "O", "B-ORG", "E-ORG")
    assert convert(converted, source="bioes", target="ioes") == tags
