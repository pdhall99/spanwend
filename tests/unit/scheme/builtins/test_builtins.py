"""Parallel contract tests shared by all canonical built-in schemes."""

import pytest

from spanwend import (
    DiagnosticCode,
    Span,
    TagSyntax,
    UnrepresentableError,
    check_conformance,
    check_representability,
    decode,
    encode,
)
from spanwend._scheme.builtins.registry import _SchemeKey
from tests.unit import CANONICAL_SCHEMES


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_empty_sequence_round_trips(scheme: _SchemeKey) -> None:
    assert check_conformance([], scheme=scheme).conformant
    assert decode([], scheme=scheme) == ()
    assert check_representability([], length=0, scheme=scheme).representable
    assert encode([], length=0, scheme=scheme) == ()


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_empty_span_collection_fills_declared_length(scheme: _SchemeKey) -> None:
    tags = encode([], length=3, scheme=scheme)

    assert tags == ("O", "O", "O")
    assert check_conformance(tags, scheme=scheme).conformant
    assert decode(tags, scheme=scheme) == ()


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_labelled_spans_round_trip(scheme: _SchemeKey) -> None:
    spans = (Span(1, 3, "PER"), Span(4, 5, "ORG"))

    assert check_representability(spans, length=6, scheme=scheme).representable
    tags = encode(spans, length=6, scheme=scheme)

    assert check_conformance(tags, scheme=scheme).conformant
    assert decode(tags, scheme=scheme) == spans


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_unlabelled_spans_round_trip(scheme: _SchemeKey) -> None:
    spans = (Span(1, 3, None), Span(4, 5, None))

    assert check_representability(spans, length=6, scheme=scheme).representable
    tags = encode(spans, length=6, scheme=scheme)

    assert all("-" not in tag for tag in tags if tag != "O")
    assert check_conformance(tags, scheme=scheme).conformant
    assert decode(tags, scheme=scheme) == spans


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_unsorted_spans_encode_deterministically(scheme: _SchemeKey) -> None:
    canonical = (Span(0, 2, "PER"), Span(3, 4, "ORG"))
    unsorted = tuple(reversed(canonical))

    assert encode(unsorted, length=4, scheme=scheme) == encode(
        canonical,
        length=4,
        scheme=scheme,
    )


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_suffix_syntax_round_trips(scheme: _SchemeKey) -> None:
    syntax = TagSyntax(placement="suffix")
    spans = (Span(0, 2, "PER"), Span(3, 4, "ORG"))

    tags = encode(spans, length=4, scheme=scheme, syntax=syntax)

    assert check_conformance(tags, scheme=scheme, syntax=syntax).conformant
    assert decode(tags, scheme=scheme, syntax=syntax) == spans


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_custom_separator_and_outside_tag_round_trip(scheme: _SchemeKey) -> None:
    syntax = TagSyntax(separator="::", placement="suffix", outside="_")
    spans = (Span(0, 2, "PER"), Span(3, 4, "ORG"))

    tags = encode(spans, length=4, scheme=scheme, syntax=syntax)

    assert "_" in tags
    assert check_conformance(tags, scheme=scheme, syntax=syntax).conformant
    assert decode(tags, scheme=scheme, syntax=syntax) == spans


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_adjacent_different_label_spans_round_trip(scheme: _SchemeKey) -> None:
    spans = (Span(0, 1, "PER"), Span(1, 3, "ORG"))

    assert check_representability(spans, length=3, scheme=scheme).representable
    tags = encode(spans, length=3, scheme=scheme)

    assert decode(tags, scheme=scheme) == spans


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_adjacent_same_label_representability_is_explicit(scheme: _SchemeKey) -> None:
    spans = (Span(0, 1, "PER"), Span(1, 3, "PER"))
    result = check_representability(spans, length=3, scheme=scheme)

    if scheme == "io":
        assert not result.representable
        with pytest.raises(UnrepresentableError):
            encode(spans, length=3, scheme=scheme)
    else:
        assert result.representable
        tags = encode(spans, length=3, scheme=scheme)
        assert decode(tags, scheme=scheme) == spans


@pytest.mark.parametrize("scheme", CANONICAL_SCHEMES)
def test_labelled_outside_tag_is_rejected(scheme: _SchemeKey) -> None:
    result = check_conformance(["O-PER"], scheme=scheme)

    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        DiagnosticCode.OUTSIDE_WITH_LABEL
    ]


_README_AT_A_GLANCE: tuple[tuple[_SchemeKey, str | None], ...] = (
    ("io", None),
    ("iob1", "I-ORG B-ORG O O I-PER I-PER O I-LOC I-LOC I-LOC"),
    ("bio", "B-ORG B-ORG O O B-PER I-PER O B-LOC I-LOC I-LOC"),
    ("ioe1", "E-ORG I-ORG O O I-PER I-PER O I-LOC I-LOC I-LOC"),
    ("ioe2", "E-ORG E-ORG O O I-PER E-PER O I-LOC I-LOC E-LOC"),
    ("bios", "S-ORG S-ORG O O B-PER I-PER O B-LOC I-LOC I-LOC"),
    ("bioe", "B-ORG B-ORG O O B-PER E-PER O B-LOC I-LOC E-LOC"),
    ("ioes", "S-ORG S-ORG O O I-PER E-PER O I-LOC I-LOC E-LOC"),
    ("bioes", "S-ORG S-ORG O O B-PER E-PER O B-LOC I-LOC E-LOC"),
    ("bilou", "U-ORG U-ORG O O B-PER L-PER O B-LOC I-LOC L-LOC"),
    ("bmes", "S-ORG S-ORG O O B-PER E-PER O B-LOC M-LOC E-LOC"),
    ("bmeow", "W-ORG W-ORG O O B-PER E-PER O B-LOC M-LOC E-LOC"),
)


def test_readme_at_a_glance_example_matches_scheme_semantics() -> None:
    assert tuple(scheme for scheme, _ in _README_AT_A_GLANCE) == CANONICAL_SCHEMES
    spans = (
        Span(0, 1, "ORG"),
        Span(1, 2, "ORG"),
        Span(4, 6, "PER"),
        Span(7, 10, "LOC"),
    )

    for scheme, expected in _README_AT_A_GLANCE:
        if expected is None:
            assert not check_representability(
                spans,
                length=10,
                scheme=scheme,
            ).representable
            with pytest.raises(UnrepresentableError):
                encode(spans, length=10, scheme=scheme)
        else:
            assert encode(spans, length=10, scheme=scheme) == tuple(expected.split())
