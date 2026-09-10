"""Tests for semantics specific to the built-in BIO/IOB2 scheme."""

import pytest

from spanwend import (
    DiagnosticCode,
    InvalidTagSequenceError,
    Span,
    check_conformance,
    decode,
    encode,
)


def test_bio_marks_every_span_start_with_b() -> None:
    spans = (Span(0, 1, "PER"), Span(1, 3, "PER"), Span(4, 6, "ORG"))

    tags = encode(spans, length=6, scheme="bio")

    assert tags == ("B-PER", "B-PER", "I-PER", "O", "B-ORG", "I-ORG")
    assert decode(tags, scheme="bio") == spans


def test_bio_rejects_span_initial_i() -> None:
    tags = ["I-PER", "I-PER"]
    result = check_conformance(tags, scheme="bio")

    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        DiagnosticCode.INVALID_START
    ]
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="bio")
    assert exc_info.value.diagnostics == result.diagnostics


def test_bio_rejects_label_mismatch_inside_span() -> None:
    result = check_conformance(["B-PER", "I-ORG"], scheme="bio")

    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        DiagnosticCode.LABEL_MISMATCH
    ]


def test_iob2_alias_matches_bio_semantics() -> None:
    spans = (Span(0, 2, "PER"), Span(3, 4, "ORG"))
    tags = encode(spans, length=4, scheme="bio")

    assert encode(spans, length=4, scheme="iob2") == tags
    assert decode(tags, scheme="iob2") == spans
    assert check_conformance(tags, scheme="iob2").conformant
