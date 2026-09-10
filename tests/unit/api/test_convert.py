"""Tests for behaviour specific to the public `convert()` operation."""

import pytest

from spanwend import (
    DEFAULT_SYNTAX,
    InvalidTagSequenceError,
    Span,
    TagSyntax,
    UnrepresentableError,
    check_representability,
    convert,
    decode,
    encode,
)
from spanwend._scheme.builtins.registry import _SchemeKey
from tests.unit import CANONICAL_SCHEMES

SUFFIX_SYNTAX = TagSyntax(placement="suffix")


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_same_scheme_same_syntax_conversion_is_identity(scheme: _SchemeKey) -> None:
    spans = [Span(0, 2, "PER"), Span(3, 4, "ORG")]
    tags = encode(spans, length=5, scheme=scheme)

    assert convert(tags, source=scheme, target=scheme) == tags


@pytest.mark.parametrize("source", CANONICAL_SCHEMES)
@pytest.mark.parametrize("target", CANONICAL_SCHEMES)
def test_cross_scheme_conversion_preserves_spans(
    source: _SchemeKey,
    target: _SchemeKey,
) -> None:
    spans = [Span(0, 2, "PER"), Span(3, 4, "ORG")]
    source_tags = encode(spans, length=5, scheme=source)

    assert check_representability(spans, length=5, scheme=target).representable
    converted = convert(source_tags, source=source, target=target)

    assert decode(converted, scheme=target) == tuple(spans)


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_same_scheme_cross_syntax_conversion(scheme: _SchemeKey) -> None:
    spans = [Span(0, 2, "PER"), Span(3, 4, "ORG")]
    source_tags = encode(
        spans,
        length=5,
        scheme=scheme,
        syntax=SUFFIX_SYNTAX,
    )

    converted = convert(
        source_tags,
        source=scheme,
        target=scheme,
        source_syntax=SUFFIX_SYNTAX,
        target_syntax=DEFAULT_SYNTAX,
    )

    assert converted == encode(spans, length=5, scheme=scheme)
    assert decode(converted, scheme=scheme) == tuple(spans)


def test_cross_scheme_cross_syntax_conversion() -> None:
    source_syntax = TagSyntax(separator=":", placement="suffix", outside="_")
    target_syntax = TagSyntax(separator="|", placement="prefix", outside="NONE")
    spans = [Span(0, 1, "PER"), Span(2, 5, "ORG")]
    source_tags = encode(
        spans,
        length=5,
        scheme="bioes",
        syntax=source_syntax,
    )

    converted = convert(
        source_tags,
        source="iobes",
        target="bioul",
        source_syntax=source_syntax,
        target_syntax=target_syntax,
    )

    assert converted == ("U|PER", "NONE", "B|ORG", "I|ORG", "L|ORG")
    assert decode(
        converted,
        scheme="bilou",
        syntax=target_syntax,
    ) == tuple(spans)


def test_unlabelled_conversion_preserves_semantics() -> None:
    tags = ("B", "I", "O", "B")

    converted = convert(tags, source="bio", target="bilou")

    assert converted == ("B", "L", "O", "U")
    assert decode(converted, scheme="bilou") == (
        Span(0, 2, None),
        Span(3, 4, None),
    )


def test_aliases_have_identical_conversion_semantics() -> None:
    tags = ["B-PER", "I-PER", "O", "B-ORG"]

    assert convert(tags, source="iob2", target="iobes") == (
        "B-PER",
        "E-PER",
        "O",
        "S-ORG",
    )
    assert convert(tags, source="bio", target="bioes") == (
        "B-PER",
        "E-PER",
        "O",
        "S-ORG",
    )


def test_unrepresentable_target_propagates_error() -> None:
    source_tags = ["I-PER", "B-PER"]

    with pytest.raises(
        UnrepresentableError,
        match="adjacent spans with the same label",
    ):
        convert(source_tags, source="iob1", target="io")


def test_invalid_source_preserves_decode_diagnostics() -> None:
    tags = ["I-PER", "I-PER", "O", "I-ORG"]

    with pytest.raises(InvalidTagSequenceError) as decode_exc:
        decode(tags, scheme="bio")
    with pytest.raises(InvalidTagSequenceError) as convert_exc:
        convert(tags, source="bio", target="bilou")

    assert convert_exc.value.diagnostics == decode_exc.value.diagnostics
