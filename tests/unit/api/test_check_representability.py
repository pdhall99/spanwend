"""Tests for behaviour specific to public `check_representability()`."""

import pytest

import spanwend._api
from spanwend import (
    RepresentabilityCode,
    RepresentabilityResult,
    Span,
    UnrepresentableError,
    check_representability,
    decode,
    encode,
)
from spanwend._scheme.builtins.registry import _SchemeKey


def test_check_representability_accepts_unsorted_non_overlapping_spans() -> None:
    spans = [Span(3, 5, "ORG"), Span(0, 2, "PER")]

    assert check_representability(spans, length=5, scheme="bio") == (
        RepresentabilityResult()
    )


@pytest.mark.parametrize(
    ("scheme", "spans", "length", "code"),
    [
        (
            "bio",
            (Span(0, 2, "PER"), Span(0, 2, "PER")),
            4,
            RepresentabilityCode.DUPLICATE_SPAN,
        ),
        (
            "bio",
            (Span(2, 5, "ORG"),),
            4,
            RepresentabilityCode.SPAN_OUT_OF_BOUNDS,
        ),
        (
            "bio",
            (Span(0, 4, "ORG"), Span(1, 2, "PRODUCT")),
            4,
            RepresentabilityCode.OVERLAPPING_SPANS,
        ),
        (
            "io",
            (Span(0, 1, "PER"), Span(1, 2, "PER")),
            2,
            RepresentabilityCode.ADJACENT_SAME_LABEL,
        ),
    ],
)
def test_check_representability_returns_structured_failure(
    scheme: _SchemeKey,
    spans: tuple[Span, ...],
    length: int,
    code: RepresentabilityCode,
) -> None:
    result = check_representability(spans, length=length, scheme=scheme)

    assert not result.representable
    assert result.code is code
    assert result.message


def test_encode_raises_same_structured_representability_failure() -> None:
    spans = (Span(0, 1, "PER"), Span(1, 2, "PER"))
    result = check_representability(spans, length=2, scheme="io")

    with pytest.raises(UnrepresentableError) as caught:
        encode(spans, length=2, scheme="io")

    assert caught.value.code is result.code
    assert caught.value.message == result.message
    assert str(caught.value) == result.message


def test_representability_result_requires_code_and_message_together() -> None:
    with pytest.raises(ValueError, match="provided together"):
        RepresentabilityResult(code=RepresentabilityCode.DUPLICATE_SPAN)

    with pytest.raises(ValueError, match="provided together"):
        RepresentabilityResult(message="failure")


def test_check_representability_does_not_call_encode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_encode(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("representability check must not call encode")

    monkeypatch.setattr(spanwend._api, "encode", fail_encode)

    assert check_representability(
        [Span(0, 1, "PER")],
        length=1,
        scheme="bio",
    ).representable


def test_check_representability_rejects_non_span_item() -> None:
    with pytest.raises(TypeError, match="expected Span"):
        check_representability(
            ["not-a-span"],  # type: ignore[bad-argument-type]
            length=1,
            scheme="bio",  # type: ignore[list-item]
        )


@pytest.mark.parametrize(
    ("scheme", "spans", "length"),
    [
        ("bio", [Span(0, 1, "PER")], 1),
        ("bio", [Span(0, 2, "PER"), Span(2, 3, "PER")], 3),
        ("bio", [Span(1, 3, "ORG"), Span(4, 5, "PER")], 6),
        ("io", [Span(0, 2, "PER")], 2),
        ("io", [Span(0, 1, "PER"), Span(1, 2, "ORG")], 2),
        ("io", [Span(1, 3, "ORG"), Span(4, 5, "PER")], 6),
    ],
)
def test_representable_collections_round_trip(
    scheme: _SchemeKey,
    spans: list[Span],
    length: int,
) -> None:
    assert check_representability(spans, length=length, scheme=scheme).representable
    assert decode(encode(spans, length=length, scheme=scheme), scheme=scheme) == tuple(
        sorted(spans, key=Span._sort_key)
    )
