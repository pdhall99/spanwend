"""Tests for semantics specific to the built-in IO scheme."""

import pytest

from spanwend import (
    DiagnosticCode,
    InvalidTagSequenceError,
    Span,
    UnrepresentableError,
    check_conformance,
    check_representability,
    decode,
    encode,
)


def test_io_decodes_same_label_run_as_one_span() -> None:
    assert decode(["I-PER", "I-PER", "O"], scheme="io") == (Span(0, 2, "PER"),)


def test_io_label_change_starts_new_adjacent_span() -> None:
    tags = ["I-PER", "I-ORG", "I-ORG"]

    assert check_conformance(tags, scheme="io").conformant
    assert decode(tags, scheme="io") == (Span(0, 1, "PER"), Span(1, 3, "ORG"))


def test_io_rejects_b_marker_with_structured_diagnostic() -> None:
    result = check_conformance(["B-PER", "I-PER"], scheme="io")

    assert not result.conformant
    assert result.diagnostics[0].code is DiagnosticCode.UNSUPPORTED_MARKER
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(["B-PER", "I-PER"], scheme="io")
    assert exc_info.value.diagnostics == result.diagnostics


def test_io_adjacent_same_label_spans_raise_unrepresentable_error() -> None:
    spans = [Span(0, 1, "PER"), Span(1, 2, "PER")]

    assert not check_representability(spans, length=2, scheme="io").representable
    with pytest.raises(UnrepresentableError, match="adjacent"):
        encode(spans, length=2, scheme="io")
