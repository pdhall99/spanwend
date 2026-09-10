"""Exhaustive conformance tests over small semantic spaces."""

from collections.abc import Iterator
from itertools import product

import pytest

from spanwend import (
    InvalidTagSequenceError,
    RepairPolicy,
    Span,
    UnrepresentableError,
    check_conformance,
    check_representability,
    convert,
    decode,
    encode,
    repair,
)
from spanwend._scheme.builtins.registry import _SchemeKey
from tests.conformance._conformance import (
    IMPLEMENTED_SCHEMES,
    SemanticTag,
    format_tag,
    reference_decode,
    reference_encode,
    reference_is_representable,
    reference_is_valid,
    span_collections,
    tag_sequences,
)


@pytest.mark.parametrize("scheme", IMPLEMENTED_SCHEMES)
def test_small_tag_languages_match_independent_grammar(scheme: _SchemeKey) -> None:
    for semantic_tags in tag_sequences(scheme, max_length=3):
        tags = [format_tag(tag) for tag in semantic_tags]
        expected_valid = reference_is_valid(semantic_tags, scheme)
        result = check_conformance(tags, scheme=scheme)

        assert result.conformant is expected_valid, (scheme, tags, result.diagnostics)
        if expected_valid:
            expected_spans = reference_decode(semantic_tags, scheme)
            spans = decode(tags, scheme=scheme)
            assert spans == expected_spans
            assert encode(spans, length=len(tags), scheme=scheme) == tuple(tags)
            assert convert(tags, source=scheme, target=scheme) == tuple(tags)
        else:
            with pytest.raises(InvalidTagSequenceError) as exc_info:
                decode(tags, scheme=scheme)
            assert exc_info.value.diagnostics == result.diagnostics


@pytest.mark.parametrize("scheme", IMPLEMENTED_SCHEMES)
def test_small_span_collections_match_independent_representability(
    scheme: _SchemeKey,
) -> None:
    for length in range(4):
        collections = list(span_collections(length))
        if length < 3:
            collections.append((Span(length, length + 1, "PER"),))

        for spans in collections:
            expected = reference_is_representable(
                spans,
                length=length,
                scheme=scheme,
            )
            assert (
                check_representability(
                    spans, length=length, scheme=scheme
                ).representable
                is expected
            )
            if expected:
                expected_tags = reference_encode(
                    spans,
                    length=length,
                    scheme=scheme,
                )
                assert encode(spans, length=length, scheme=scheme) == expected_tags
                assert decode(expected_tags, scheme=scheme) == tuple(
                    sorted(spans, key=lambda span: (span.start, span.end, span.label))
                )
            else:
                with pytest.raises(UnrepresentableError):
                    encode(spans, length=length, scheme=scheme)


@pytest.mark.parametrize("source", IMPLEMENTED_SCHEMES)
def test_small_valid_languages_obey_guarded_cross_scheme_conversion(
    source: _SchemeKey,
) -> None:
    for semantic_tags in tag_sequences(source, max_length=3):
        if not reference_is_valid(semantic_tags, source):
            continue
        source_tags = [format_tag(tag) for tag in semantic_tags]
        spans = reference_decode(semantic_tags, source)

        for target in IMPLEMENTED_SCHEMES:
            if reference_is_representable(
                spans,
                length=len(source_tags),
                scheme=target,
            ):
                expected = reference_encode(
                    spans,
                    length=len(source_tags),
                    scheme=target,
                )
                converted = convert(source_tags, source=source, target=target)
                assert converted == expected
                assert decode(converted, scheme=target) == spans
            else:
                with pytest.raises(UnrepresentableError):
                    convert(source_tags, source=source, target=target)


def _formatted_sequences(
    semantic_alphabet: tuple[SemanticTag, ...], max_length: int
) -> Iterator[list[str]]:
    for length in range(max_length + 1):
        for tags in product(semantic_alphabet, repeat=length):
            yield [format_tag(tag) for tag in tags]


@pytest.mark.parametrize("policy", tuple(RepairPolicy))
def test_small_bio_repair_domain_always_satisfies_postcondition(
    policy: RepairPolicy,
) -> None:
    alphabet: tuple[SemanticTag, ...] = (
        ("O", None),
        ("B", "PER"),
        ("I", "PER"),
        ("B", "ORG"),
        ("I", "ORG"),
    )
    for tags in _formatted_sequences(alphabet, max_length=3):
        result = repair(tags, scheme="bio", policy=policy)
        assert check_conformance(result.tags, scheme="bio").conformant
        decode(result.tags, scheme="bio")
        assert result.changed is (result.tags != tuple(tags))


def test_small_iob1_repair_domain_always_satisfies_postcondition() -> None:
    alphabet: tuple[SemanticTag, ...] = (
        ("O", None),
        ("I", "PER"),
        ("B", "PER"),
        ("I", "ORG"),
        ("B", "ORG"),
    )
    for tags in _formatted_sequences(alphabet, max_length=3):
        result = repair(tags, scheme="iob1", policy="conlleval")
        assert check_conformance(result.tags, scheme="iob1").conformant
        decode(result.tags, scheme="iob1")
        assert result.changed is (result.tags != tuple(tags))
