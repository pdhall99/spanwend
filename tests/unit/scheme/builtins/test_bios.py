"""Tests for semantics specific to the BIOS built-in."""

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


def test_bios_encodes_singleton_and_multi_token_spans() -> None:
    spans = [
        Span(0, 1, "PER"),
        Span(2, 4, "ORG"),
        Span(5, 8, "LOC"),
        Span(9, 13, "MISC"),
    ]

    tags = encode(spans, length=13, scheme="bios")

    assert tags == (
        "S-PER",
        "O",
        "B-ORG",
        "I-ORG",
        "O",
        "B-LOC",
        "I-LOC",
        "I-LOC",
        "O",
        "B-MISC",
        "I-MISC",
        "I-MISC",
        "I-MISC",
    )
    assert decode(tags, scheme="bios") == tuple(spans)


@pytest.mark.parametrize(
    ("tags", "codes", "indices"),
    [
        (["I-PER"], [DiagnosticCode.INVALID_START], [0]),
        (["B-PER"], [DiagnosticCode.UNTERMINATED_SPAN], [0]),
        (["B-PER", "O"], [DiagnosticCode.INVALID_TRANSITION], [1]),
        (["B-PER", "S-ORG"], [DiagnosticCode.INVALID_TRANSITION], [1]),
        (["B-PER", "B-ORG"], [DiagnosticCode.INVALID_TRANSITION], [1]),
        (["B-PER", "I-ORG"], [DiagnosticCode.LABEL_MISMATCH], [1]),
        (["E-PER"], [DiagnosticCode.UNSUPPORTED_MARKER], [0]),
    ],
)
def test_bios_rejects_invalid_sequences_without_cascading_diagnostics(
    tags: list[str],
    codes: list[DiagnosticCode],
    indices: list[int],
) -> None:
    result = check_conformance(tags, scheme="bios")

    assert [diagnostic.code for diagnostic in result.diagnostics] == codes
    assert [diagnostic.index for diagnostic in result.diagnostics] == indices
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="bios")
    assert exc_info.value.diagnostics == result.diagnostics


def test_bios_converts_through_canonical_spans() -> None:
    tags = ("S-PER", "O", "B-ORG", "I-ORG", "I-ORG")

    converted = convert(tags, source="bios", target="bioes")

    assert converted == ("S-PER", "O", "B-ORG", "I-ORG", "E-ORG")
    assert convert(converted, source="bioes", target="bios") == tags
