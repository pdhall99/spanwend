"""Tests for behaviour specific to the public `decode()` operation."""

import pytest

from spanwend import InvalidTagSequenceError, Span, TagSyntax, check_conformance, decode


def test_decode_bio_to_right_open_spans() -> None:
    tags = ["B-PER", "I-PER", "O", "B-ORG", "O", "B-LOC", "I-LOC"]

    assert check_conformance(tags, scheme="bio").conformant
    assert decode(tags, scheme="bio") == (
        Span(0, 2, "PER"),
        Span(3, 4, "ORG"),
        Span(5, 7, "LOC"),
    )


def test_decode_unlabelled_bio_sequence_to_unlabelled_spans() -> None:
    tags = ("O", "O", "B", "I", "O", "B", "I", "O", "O", "O")

    assert check_conformance(tags, scheme="bio").conformant
    assert decode(tags, scheme="bio") == (
        Span(2, 4, None),
        Span(5, 7, None),
    )


def test_decode_bio_b_tag_closes_previous_span() -> None:
    assert decode(["B-PER", "B-ORG"], scheme="bio") == (
        Span(0, 1, "PER"),
        Span(1, 2, "ORG"),
    )


def test_decode_supports_suffix_syntax() -> None:
    syntax = TagSyntax(placement="suffix")

    assert decode(["PER-B", "PER-I", "O", "ORG-B"], scheme="bio", syntax=syntax) == (
        Span(0, 2, "PER"),
        Span(3, 4, "ORG"),
    )


def test_decode_respects_custom_outside_tag() -> None:
    syntax = TagSyntax(outside="OUT")

    assert decode(["B-PER", "OUT", "B-ORG"], scheme="bio", syntax=syntax) == (
        Span(0, 1, "PER"),
        Span(2, 3, "ORG"),
    )


def test_decode_exception_has_exact_conformance_diagnostics() -> None:
    tags = ["I-PER", "O", "B-", "E-ORG", "I-LOC"]
    result = check_conformance(tags, scheme="bio")

    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="bio")

    assert exc_info.value.diagnostics == result.diagnostics
    assert "first at index 0" in str(exc_info.value)
