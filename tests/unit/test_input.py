"""Tests for public-input normalization and tag-sequence boundaries."""

from collections.abc import Callable, Iterable, Iterator
from typing import Any

import pytest

from spanwend import (
    Span,
    SpanInput,
    SpanMapping,
    check_conformance,
    check_representability,
    convert,
    decode,
    encode,
    repair,
)
from spanwend._input import _normalize_spans, _normalize_tags

TagOperation = Callable[[Any], object]
SpanOperation = Callable[[Iterable[SpanInput]], bool]

_TAG_OPERATIONS: tuple[TagOperation, ...] = (
    lambda tags: decode(tags, scheme="bio"),
    lambda tags: check_conformance(tags, scheme="bio"),
    lambda tags: repair(tags, scheme="bio", policy="conlleval"),
    lambda tags: convert(tags, source="bio", target="bio"),
)
_SPAN_OPERATIONS: tuple[SpanOperation, ...] = (
    lambda spans: encode(spans, length=3, scheme="bio") == ("B-PER", "O", "B-ORG"),
    lambda spans: (
        check_representability(
            spans,
            length=3,
            scheme="bio",
        ).representable
    ),
)


class _BrokenTags:
    def __iter__(self) -> Iterator[object]:
        raise TypeError("broken iterator")


class _AttributeSpan:
    start = 0
    end = 1
    label = "PER"


def test_normalize_tags_materializes_generator() -> None:
    tags = (tag for tag in ("B", "I", "O"))

    assert _normalize_tags(tags) == ("B", "I", "O")


def test_normalize_tags_rejects_scalar_string() -> None:
    with pytest.raises(TypeError, match="expected an iterable of tag strings"):
        _normalize_tags("BIO")


def test_normalize_tags_rejects_scalar_bytes() -> None:
    with pytest.raises(TypeError, match="expected an iterable of tag strings"):
        _normalize_tags(b"BIO")


def test_normalize_tags_rejects_non_string_element() -> None:
    tags: Iterable[object] = ("O", 3, "B")

    with pytest.raises(TypeError, match=r"tags\[1\]: expected str, got int"):
        _normalize_tags(tags)


def test_normalize_tags_rejects_broken_iterable() -> None:
    with pytest.raises(TypeError, match="expected an iterable of tag strings"):
        _normalize_tags(_BrokenTags())


def test_normalize_spans_accepts_supported_forms_and_returns_canonical_order() -> None:
    inputs: list[SpanInput] = [
        SpanMapping(start=4, end=5, label="ORG"),
        (0, 2, "PER"),
        Span(2, 3, "LOC"),
    ]

    assert _normalize_spans(inputs) == (
        Span(0, 2, "PER"),
        Span(2, 3, "LOC"),
        Span(4, 5, "ORG"),
    )


def test_public_span_operations_accept_tuple_inputs() -> None:
    spans: list[SpanInput] = [(0, 2, "PER"), (3, 5, "ORG")]

    assert check_representability(spans, length=5, scheme="bio").representable
    assert encode(spans, length=5, scheme="bio") == (
        "B-PER",
        "I-PER",
        "O",
        "B-ORG",
        "I-ORG",
    )


def test_public_span_operations_accept_mapping_inputs() -> None:
    spans: list[SpanInput] = [
        SpanMapping(start=0, end=2, label="PER"),
        SpanMapping(start=3, end=5, label="ORG"),
    ]

    assert check_representability(spans, length=5, scheme="bio").representable
    assert encode(spans, length=5, scheme="bio") == (
        "B-PER",
        "I-PER",
        "O",
        "B-ORG",
        "I-ORG",
    )


def test_public_span_operations_accept_unlabelled_tuple_and_mapping_inputs() -> None:
    spans: list[SpanInput] = [
        (0, 2),
        SpanMapping(start=3, end=4),
    ]

    assert check_representability(spans, length=4, scheme="bio").representable
    assert encode(spans, length=4, scheme="bio") == ("B", "I", "O", "B")


@pytest.mark.parametrize("operation", _SPAN_OPERATIONS)
def test_span_operations_materialize_generator_once(operation: SpanOperation) -> None:
    consumed = 0

    def spans() -> Iterator[SpanInput]:
        nonlocal consumed
        consumed += 1
        yield (2, 3, "ORG")
        yield SpanMapping(start=0, end=1, label="PER")

    assert operation(spans())
    assert consumed == 1


def test_span_inputs_reject_mixed_label_modes() -> None:
    spans: list[SpanInput] = [(0, 1), SpanMapping(start=2, end=3, label="PER")]

    with pytest.raises(ValueError, match="cannot be mixed"):
        encode(spans, length=3, scheme="bio")
    with pytest.raises(ValueError, match="cannot be mixed"):
        check_representability(spans, length=3, scheme="bio")


@pytest.mark.parametrize("span", [(0,), (0, 1, "PER", "extra")])
def test_span_inputs_reject_malformed_tuple_lengths(span: object) -> None:
    with pytest.raises(TypeError, match="expected a 2- or 3-item span tuple"):
        _normalize_spans([span])


def test_span_inputs_reject_mapping_missing_required_key() -> None:
    with pytest.raises(ValueError, match="missing required key.*'end'"):
        _normalize_spans([{"start": 0, "label": "PER"}])


def test_span_inputs_reject_mapping_with_extra_key() -> None:
    with pytest.raises(ValueError, match="unsupported key.*'score'"):
        _normalize_spans([{"start": 0, "end": 1, "score": 0.9}])


@pytest.mark.parametrize("span", [[0, 1], _AttributeSpan()])
def test_span_inputs_reject_unsupported_duck_typed_forms(span: object) -> None:
    with pytest.raises(
        TypeError, match="expected Span, a 2- or 3-item tuple, or a mapping"
    ):
        _normalize_spans([span])


def test_span_input_field_values_use_canonical_span_validation() -> None:
    with pytest.raises(ValueError, match="greater than start"):
        _normalize_spans([(1, 1)])
    with pytest.raises(ValueError, match="non-blank"):
        _normalize_spans([{"start": 0, "end": 1, "label": " "}])


@pytest.mark.parametrize("operation", _TAG_OPERATIONS)
@pytest.mark.parametrize("tags", ["O", b"O"])
def test_public_tag_operations_reject_scalar_string_like_inputs(
    operation: TagOperation,
    tags: object,
) -> None:
    with pytest.raises(TypeError, match="expected an iterable of tag strings"):
        operation(tags)


@pytest.mark.parametrize("operation", _TAG_OPERATIONS)
def test_public_tag_operations_reject_non_iterables(operation: TagOperation) -> None:
    with pytest.raises(TypeError, match="expected an iterable of tag strings"):
        operation(3)


@pytest.mark.parametrize("operation", _TAG_OPERATIONS)
def test_generator_iteration_type_errors_are_not_rewritten(
    operation: TagOperation,
) -> None:
    def tags():
        yield "O"
        raise TypeError("boom")

    with pytest.raises(TypeError, match="boom"):
        operation(tags())
