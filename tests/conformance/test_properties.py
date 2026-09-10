"""Property-based tests for cross-scheme semantic contracts."""

from __future__ import annotations

from typing import Any

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import assume, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from spanwend import (  # noqa: E402
    InvalidTagSequenceError,
    RepairPolicy,
    Span,
    TagSyntax,
    UnrepresentableError,
    check_conformance,
    check_representability,
    convert,
    decode,
    encode,
    repair,
)
from spanwend._scheme.builtins.registry import _SchemeKey  # noqa: E402
from tests.conformance._conformance import (  # noqa: E402
    IMPLEMENTED_SCHEMES,
    SYNTAXES,
    format_tag,
    normalize,
    reference_decode,
    reference_encode,
    reference_is_representable,
    reference_is_valid,
    reference_representability_issue,
    semantic_alphabet,
)

LABEL_STRATEGY = st.sampled_from(("PER", "ORG", "O", "WORK-OF-ART"))
SCHEME_STRATEGY = st.sampled_from(IMPLEMENTED_SCHEMES)
SYNTAX_STRATEGY = st.sampled_from(SYNTAXES)


@st.composite
def intrinsic_spans(draw: Any) -> Span:
    """Generate intrinsically valid half-open spans independently."""
    start = draw(st.integers(min_value=0, max_value=8))
    width = draw(st.integers(min_value=1, max_value=5))
    return Span(start, start + width, draw(LABEL_STRATEGY))


@st.composite
def strict_valid_tag_cases(
    draw: Any,
) -> tuple[_SchemeKey, TagSyntax, list[tuple[str, str | None]]]:
    """Generate strict-valid semantic tags from the independent grammar."""
    scheme = draw(SCHEME_STRATEGY)
    syntax = draw(SYNTAX_STRATEGY)
    semantic_tags = draw(
        st.lists(st.sampled_from(semantic_alphabet(scheme)), max_size=5)
    )
    assume(reference_is_valid(semantic_tags, scheme))
    return scheme, syntax, semantic_tags


@st.composite
def representable_cases(draw: Any) -> tuple[int, list[Span]]:
    """Generate universally representable collections without using spanwend."""
    length = draw(st.integers(min_value=0, max_value=8))
    if length == 0:
        return 0, []

    requested = draw(st.integers(min_value=0, max_value=min(4, length)))
    cursor = 0
    spans: list[Span] = []
    for _ in range(requested):
        if cursor >= length:
            break
        start = draw(st.integers(min_value=cursor, max_value=length - 1))
        end = draw(st.integers(min_value=start + 1, max_value=length))
        label = draw(LABEL_STRATEGY)
        spans.append(Span(start, end, label))
        cursor = end
    return length, spans


@st.composite
def one_universal_failure(draw: Any) -> tuple[int, list[Span], str]:
    """Generate a collection whose first independent failure has one category."""
    failure = draw(st.sampled_from(("duplicate", "overlap", "out_of_bounds")))

    if failure == "duplicate":
        length = draw(st.integers(min_value=1, max_value=8))
        start = draw(st.integers(min_value=0, max_value=length - 1))
        end = draw(st.integers(min_value=start + 1, max_value=length))
        label = draw(LABEL_STRATEGY)
        span = Span(start, end, label)
        return length, [span, span], failure

    if failure == "overlap":
        length = draw(st.integers(min_value=2, max_value=8))
        first_start = draw(st.integers(min_value=0, max_value=length - 2))
        second_start = draw(
            st.integers(min_value=first_start + 1, max_value=length - 1)
        )
        first_end = draw(st.integers(min_value=second_start + 1, max_value=length))
        second_end = draw(st.integers(min_value=second_start + 1, max_value=length))
        first = Span(first_start, first_end, draw(LABEL_STRATEGY))
        second = Span(second_start, second_end, draw(LABEL_STRATEGY))
        return length, [first, second], failure

    length = draw(st.integers(min_value=0, max_value=8))
    start = draw(st.integers(min_value=0, max_value=length))
    end = draw(st.integers(min_value=max(start + 1, length + 1), max_value=length + 4))
    span = Span(start, end, draw(LABEL_STRATEGY))
    return length, [span], failure


@st.composite
def io_loss_cases(draw: Any) -> tuple[int, list[Span]]:
    """Generate IO's scheme-specific adjacent-same-label loss case."""
    length = draw(st.integers(min_value=2, max_value=8))
    split = draw(st.integers(min_value=1, max_value=length - 1))
    first_start = draw(st.integers(min_value=0, max_value=split - 1))
    second_end = draw(st.integers(min_value=split + 1, max_value=length))
    label = draw(LABEL_STRATEGY)
    return length, [Span(first_start, split, label), Span(split, second_end, label)]


@settings(max_examples=50, deadline=None)
@given(span=intrinsic_spans())
def test_intrinsic_span_generator_obeys_span_contract(span: Span) -> None:
    assert span.start >= 0
    assert span.end > span.start
    assert span.label


@settings(max_examples=150, deadline=None)
@given(case=representable_cases(), scheme=SCHEME_STRATEGY, syntax=SYNTAX_STRATEGY)
def test_representable_span_round_trip_matches_reference(
    case: tuple[int, list[Span]],
    scheme: _SchemeKey,
    syntax: TagSyntax,
) -> None:
    length, spans = case
    assume(reference_is_representable(spans, length=length, scheme=scheme))

    expected = reference_encode(
        spans,
        length=length,
        scheme=scheme,
        syntax=syntax,
    )
    assert check_representability(spans, length=length, scheme=scheme).representable
    assert encode(spans, length=length, scheme=scheme, syntax=syntax) == expected
    assert decode(expected, scheme=scheme, syntax=syntax) == normalize(spans)


@settings(max_examples=100, deadline=None)
@given(case=one_universal_failure(), scheme=SCHEME_STRATEGY)
def test_universal_unrepresentability_matches_reference(
    case: tuple[int, list[Span], str],
    scheme: _SchemeKey,
) -> None:
    length, spans, expected_issue = case

    assert (
        reference_representability_issue(spans, length=length, scheme=scheme)
        == expected_issue
    )
    assert not check_representability(
        spans,
        length=length,
        scheme=scheme,
    ).representable
    with pytest.raises(UnrepresentableError):
        encode(spans, length=length, scheme=scheme)


@settings(max_examples=75, deadline=None)
@given(case=io_loss_cases())
def test_io_scheme_specific_loss_matches_reference(
    case: tuple[int, list[Span]],
) -> None:
    length, spans = case

    assert (
        reference_representability_issue(spans, length=length, scheme="io")
        == "io_adjacent_same_label"
    )
    assert not check_representability(spans, length=length, scheme="io").representable
    with pytest.raises(UnrepresentableError):
        encode(spans, length=length, scheme="io")


@settings(max_examples=150, deadline=None)
@given(case=strict_valid_tag_cases())
def test_grammar_generated_strict_tags_reencode_identically(
    case: tuple[_SchemeKey, TagSyntax, list[tuple[str, str | None]]],
) -> None:
    scheme, syntax, semantic_tags = case
    tags = tuple(format_tag(tag, syntax) for tag in semantic_tags)
    expected_spans = reference_decode(semantic_tags, scheme)

    assert check_conformance(tags, scheme=scheme, syntax=syntax).conformant
    decoded = decode(tags, scheme=scheme, syntax=syntax)
    assert decoded == expected_spans
    assert encode(decoded, length=len(tags), scheme=scheme, syntax=syntax) == tags
    assert (
        convert(
            tags,
            source=scheme,
            target=scheme,
            source_syntax=syntax,
            target_syntax=syntax,
        )
        == tags
    )


@settings(max_examples=150, deadline=None)
@given(
    case=representable_cases(),
    source=SCHEME_STRATEGY,
    target=SCHEME_STRATEGY,
    source_syntax=SYNTAX_STRATEGY,
    target_syntax=SYNTAX_STRATEGY,
)
def test_guarded_cross_scheme_conversion_invariance(
    case: tuple[int, list[Span]],
    source: _SchemeKey,
    target: _SchemeKey,
    source_syntax: TagSyntax,
    target_syntax: TagSyntax,
) -> None:
    length, spans = case
    assume(reference_is_representable(spans, length=length, scheme=source))
    source_tags = reference_encode(
        spans,
        length=length,
        scheme=source,
        syntax=source_syntax,
    )

    if reference_is_representable(spans, length=length, scheme=target):
        converted = convert(
            source_tags,
            source=source,
            target=target,
            source_syntax=source_syntax,
            target_syntax=target_syntax,
        )
        assert decode(converted, scheme=target, syntax=target_syntax) == normalize(
            spans
        )
    else:
        with pytest.raises(UnrepresentableError):
            convert(
                source_tags,
                source=source,
                target=target,
                source_syntax=source_syntax,
                target_syntax=target_syntax,
            )


BIO_TAG = st.sampled_from(("O", "B-PER", "I-PER", "B-ORG", "I-ORG"))
IOB1_TAG = st.sampled_from(("O", "I-PER", "B-PER", "I-ORG", "B-ORG"))


@settings(max_examples=100, deadline=None)
@given(tags=st.lists(BIO_TAG, max_size=8), policy=st.sampled_from(tuple(RepairPolicy)))
def test_bio_repair_postcondition_property(
    tags: list[str], policy: RepairPolicy
) -> None:
    result = repair(tags, scheme="bio", policy=policy)

    assert check_conformance(result.tags, scheme="bio").conformant
    decode(result.tags, scheme="bio")
    assert result.changed is (tuple(tags) != result.tags)


@settings(max_examples=100, deadline=None)
@given(tags=st.lists(IOB1_TAG, max_size=8))
def test_iob1_repair_postcondition_property(tags: list[str]) -> None:
    result = repair(tags, scheme="iob1", policy="conlleval")

    assert check_conformance(result.tags, scheme="iob1").conformant
    decode(result.tags, scheme="iob1")
    assert result.changed is (tuple(tags) != result.tags)


def test_property_module_rejects_invalid_source_with_exact_diagnostics() -> None:
    tags = ["I-PER", "O", "I-ORG"]
    result = check_conformance(tags, scheme="bio")

    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="bio")
    assert exc_info.value.diagnostics == result.diagnostics
