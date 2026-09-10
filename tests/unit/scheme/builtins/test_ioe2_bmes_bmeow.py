"""Tests for semantics specific to IOE2, BMES, and BMEOW/BMEWO."""

import pytest

from spanwend import (
    DiagnosticCode,
    InvalidTagSequenceError,
    Span,
    check_conformance,
    decode,
    encode,
)
from spanwend._scheme.builtins.registry import _SchemeKey


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        (
            "ioe2",
            (
                "E-PER",
                "O",
                "I-ORG",
                "E-ORG",
                "O",
                "I-LOC",
                "I-LOC",
                "E-LOC",
            ),
        ),
        (
            "bmes",
            (
                "S-PER",
                "O",
                "B-ORG",
                "E-ORG",
                "O",
                "B-LOC",
                "M-LOC",
                "E-LOC",
            ),
        ),
        (
            "bmeow",
            (
                "W-PER",
                "O",
                "B-ORG",
                "E-ORG",
                "O",
                "B-LOC",
                "M-LOC",
                "E-LOC",
            ),
        ),
    ],
)
def test_ioe2_bmes_bmeow_encode_span_lengths(
    scheme: _SchemeKey,
    expected: tuple[str, ...],
) -> None:
    spans = [Span(0, 1, "PER"), Span(2, 4, "ORG"), Span(5, 8, "LOC")]

    tags = encode(spans, length=8, scheme=scheme)

    assert tags == expected
    assert decode(tags, scheme=scheme) == tuple(spans)


def test_bmewo_alias_matches_bmeow() -> None:
    spans = [Span(0, 1, "PER"), Span(1, 4, "ORG")]

    expected = encode(spans, length=4, scheme="bmeow")

    assert encode(spans, length=4, scheme="bmewo") == expected
    assert decode(expected, scheme="bmewo") == tuple(spans)
    assert check_conformance(expected, scheme="bmewo").conformant


@pytest.mark.parametrize(
    ("scheme", "tags"),
    [
        ("ioe2", ["E-PER", "O", "I-ORG", "E-ORG"]),
        ("ioe2", ["I-PER", "I-PER", "E-PER", "E-ORG"]),
        ("bmes", ["S-PER", "O", "B-ORG", "E-ORG"]),
        ("bmes", ["B-PER", "M-PER", "E-PER", "S-ORG"]),
        ("bmeow", ["W-PER", "O", "B-ORG", "E-ORG"]),
        ("bmeow", ["B-PER", "M-PER", "E-PER", "W-ORG"]),
    ],
)
def test_strict_conformant_input_reencodes_identically(
    scheme: _SchemeKey,
    tags: list[str],
) -> None:
    assert check_conformance(tags, scheme=scheme).conformant
    spans = decode(tags, scheme=scheme)

    assert encode(spans, length=len(tags), scheme=scheme) == tuple(tags)


@pytest.mark.parametrize(
    ("tags", "code", "index"),
    [
        (["I-PER"], DiagnosticCode.UNTERMINATED_SPAN, 0),
        (["I-PER", "O"], DiagnosticCode.INVALID_TRANSITION, 1),
        (["I-PER", "I-ORG", "E-ORG"], DiagnosticCode.LABEL_MISMATCH, 1),
        (["I-PER", "E-ORG"], DiagnosticCode.LABEL_MISMATCH, 1),
        (["B-PER"], DiagnosticCode.UNSUPPORTED_MARKER, 0),
    ],
)
def test_ioe2_rejects_invalid_sequences(
    tags: list[str],
    code: DiagnosticCode,
    index: int,
) -> None:
    result = check_conformance(tags, scheme="ioe2")

    assert result.diagnostics[0].code is code
    assert result.diagnostics[0].index == index
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="ioe2")
    assert exc_info.value.diagnostics == result.diagnostics


@pytest.mark.parametrize(
    ("scheme", "middle", "single"),
    [("bmes", "M", "S"), ("bmeow", "M", "W")],
)
def test_middle_marker_schemes_reject_invalid_boundaries_and_labels(
    scheme: _SchemeKey,
    middle: str,
    single: str,
) -> None:
    cases = [
        ([f"{middle}-PER"], DiagnosticCode.INVALID_START, 0),
        (["E-PER"], DiagnosticCode.INVALID_START, 0),
        (["B-PER", "O"], DiagnosticCode.INVALID_TRANSITION, 1),
        (
            ["B-PER", f"{middle}-ORG", "E-ORG"],
            DiagnosticCode.LABEL_MISMATCH,
            1,
        ),
        (["B-PER", f"{middle}-PER"], DiagnosticCode.UNTERMINATED_SPAN, 1),
        (["I-PER"], DiagnosticCode.UNSUPPORTED_MARKER, 0),
    ]

    for tags, code, index in cases:
        result = check_conformance(tags, scheme=scheme)
        assert result.diagnostics[0].code is code
        assert result.diagnostics[0].index == index

    assert check_conformance([f"{single}-PER"], scheme=scheme).conformant
