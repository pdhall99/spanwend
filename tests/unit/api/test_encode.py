"""Tests for behaviour specific to the public `encode()` operation."""

import pytest

from spanwend import Span, TagSyntax, check_representability, decode, encode
from spanwend._scheme.builtins.registry import _SchemeKey


def test_encode_is_deterministic_for_unsorted_spans() -> None:
    spans = [Span(3, 5, "ORG"), Span(0, 2, "PER")]

    assert encode(spans, length=6, scheme="bio") == (
        "B-PER",
        "I-PER",
        "O",
        "B-ORG",
        "I-ORG",
        "O",
    )


def test_encode_empty_collection_fills_declared_length_with_outside_tags() -> None:
    assert encode([], length=4, scheme="bio") == ("O", "O", "O", "O")
    assert encode([], length=3, scheme="io", syntax=TagSyntax(outside="OUT")) == (
        "OUT",
        "OUT",
        "OUT",
    )


def test_encode_supports_suffix_syntax() -> None:
    syntax = TagSyntax(placement="suffix")

    assert encode([Span(0, 2, "PER")], length=3, scheme="bio", syntax=syntax) == (
        "PER-B",
        "PER-I",
        "O",
    )


def test_encode_rejects_outside_tag_collision() -> None:
    syntax = TagSyntax(outside="I")

    assert check_representability(
        [Span(0, 1, None)],
        length=1,
        scheme="io",
    ).representable
    with pytest.raises(ValueError, match="TagSyntax.outside"):
        encode([Span(0, 1, None)], length=1, scheme="io", syntax=syntax)


@pytest.mark.parametrize(
    ("scheme", "span", "syntax"),
    [
        ("bio", Span(0, 1, "PER"), TagSyntax(separator="B")),
        ("bio", Span(0, 1, "PER"), TagSyntax(separator="BB")),
        ("io", Span(0, 1, "PER"), TagSyntax(separator="I")),
        ("io", Span(0, 1, "PER"), TagSyntax(separator="II")),
        ("io", Span(0, 1, "PER"), TagSyntax(separator="I", placement="suffix")),
        ("io", Span(0, 1, "PER"), TagSyntax(separator="II", placement="suffix")),
        ("bilou", Span(0, 2, "PER"), TagSyntax(separator="L")),
        ("bilou", Span(0, 1, "PER"), TagSyntax(separator="U", placement="suffix")),
    ],
)
def test_encode_rejects_separator_collision(
    scheme: _SchemeKey,
    span: Span,
    syntax: TagSyntax,
) -> None:
    with pytest.raises(ValueError, match="TagSyntax.separator"):
        encode([span], length=span.end, scheme=scheme, syntax=syntax)


@pytest.mark.parametrize(
    "syntax",
    [
        TagSyntax(),
        TagSyntax(separator="::", placement="suffix"),
        TagSyntax(separator="BI"),
        TagSyntax(separator="IB", placement="suffix"),
    ],
)
def test_encode_preserves_labels_with_separators_and_markers(
    syntax: TagSyntax,
) -> None:
    spans = (Span(0, 3, "ORG::BI-IB"),)

    tags = encode(spans, length=4, scheme="bio", syntax=syntax)

    assert decode(tags, scheme="bio", syntax=syntax) == spans
