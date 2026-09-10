"""Parallel contract tests for all public operations in `spanwend._api`."""

from collections.abc import Iterator
from typing import Generic, TypeVar

import pytest

from spanwend import (
    ConformanceResult,
    RepairResult,
    RepresentabilityResult,
    Span,
    check_conformance,
    check_representability,
    convert,
    decode,
    encode,
    repair,
)

_T = TypeVar("_T")


class _OneShot(Generic[_T]):
    """Iterable that fails if a public operation consumes it more than once."""

    def __init__(self, values: list[_T]) -> None:
        self._values = values
        self.iterations = 0

    def __iter__(self) -> Iterator[_T]:
        self.iterations += 1
        if self.iterations > 1:
            raise AssertionError("input iterable was consumed more than once")
        yield from self._values


# Empty input


def test_decode_empty_input() -> None:
    assert decode([], scheme="bio") == ()


def test_encode_empty_input() -> None:
    assert encode([], length=0, scheme="bio") == ()


def test_convert_empty_input() -> None:
    assert convert([], source="bio", target="bilou") == ()


def test_repair_empty_input() -> None:
    assert repair([], scheme="bio", policy="discard") == RepairResult(
        tags=(), diagnostics=(), changed=False
    )


def test_check_conformance_empty_input() -> None:
    assert check_conformance([], scheme="bio") == ConformanceResult(())


def test_check_representability_empty_input() -> None:
    assert (
        check_representability([], length=0, scheme="bio") == RepresentabilityResult()
    )


# Generic iterable input


def test_decode_materializes_input_once() -> None:
    tags = _OneShot(["B-PER", "I-PER"])

    assert decode(tags, scheme="bio") == (Span(0, 2, "PER"),)
    assert tags.iterations == 1


def test_encode_materializes_input_once() -> None:
    spans = _OneShot([Span(2, 3, "ORG"), Span(0, 1, "PER")])

    assert encode(spans, length=3, scheme="bio") == ("B-PER", "O", "B-ORG")
    assert spans.iterations == 1


def test_convert_materializes_input_once() -> None:
    tags = _OneShot(["B-PER", "I-PER", "O", "B-ORG"])

    assert convert(tags, source="bio", target="bilou") == (
        "B-PER",
        "L-PER",
        "O",
        "U-ORG",
    )
    assert tags.iterations == 1


def test_repair_materializes_input_once() -> None:
    tags = _OneShot(["I-PER", "I-PER"])

    assert repair(tags, scheme="bio", policy="conlleval").tags == (
        "B-PER",
        "I-PER",
    )
    assert tags.iterations == 1


def test_check_conformance_materializes_input_once() -> None:
    tags = _OneShot(["B-PER", "I-PER"])

    assert check_conformance(tags, scheme="bio").conformant
    assert tags.iterations == 1


def test_check_representability_materializes_input_once() -> None:
    spans = _OneShot([Span(0, 1, "PER")])

    assert check_representability(spans, length=1, scheme="bio").representable
    assert spans.iterations == 1


# Scheme resolution


def test_decode_accepts_case_insensitive_alias() -> None:
    result = decode(
        ["B-PER"],
        scheme="IOB2",  # type: ignore[arg-type]
    )

    assert result == (Span(0, 1, "PER"),)


def test_encode_accepts_case_insensitive_alias() -> None:
    result = encode(
        [Span(0, 1, "PER")],
        length=1,
        scheme="IOB2",  # type: ignore[arg-type]
    )

    assert result == ("B-PER",)


def test_convert_accepts_case_insensitive_aliases() -> None:
    assert convert(
        ["B-PER"],
        source="IOB2",  # type: ignore[arg-type]
        target="IOBES",  # type: ignore[arg-type]
    ) == ("S-PER",)


def test_repair_accepts_case_insensitive_alias() -> None:
    assert repair(
        ["I-PER"],
        scheme="IOB2",  # type: ignore[arg-type]
        policy="CONLLEVAL",
    ).tags == ("B-PER",)


def test_check_conformance_accepts_case_insensitive_alias() -> None:
    assert check_conformance(
        ["B-PER"],
        scheme="IOB2",  # type: ignore[arg-type]
    ).conformant


def test_check_representability_accepts_case_insensitive_alias() -> None:
    assert check_representability(
        [Span(0, 1, "PER")],
        length=1,
        scheme="IOB2",  # type: ignore[arg-type]
    ).representable


def test_decode_rejects_unknown_scheme() -> None:
    with pytest.raises(ValueError):
        decode([], scheme="unknown")  # type: ignore[arg-type]


def test_encode_rejects_unknown_scheme() -> None:
    with pytest.raises(ValueError):
        encode([], length=0, scheme="unknown")  # type: ignore[arg-type]


def test_convert_rejects_unknown_source_scheme() -> None:
    with pytest.raises(ValueError):
        convert([], source="unknown", target="bio")  # type: ignore[arg-type]


def test_convert_rejects_unknown_target_scheme() -> None:
    with pytest.raises(ValueError):
        convert([], source="bio", target="unknown")  # type: ignore[arg-type]


def test_repair_rejects_unknown_scheme() -> None:
    with pytest.raises(ValueError):
        repair([], scheme="unknown", policy="conlleval")  # type: ignore[arg-type]


def test_check_conformance_rejects_unknown_scheme() -> None:
    with pytest.raises(ValueError):
        check_conformance([], scheme="unknown")  # type: ignore[arg-type]


def test_check_representability_rejects_unknown_scheme() -> None:
    with pytest.raises(ValueError):
        check_representability([], length=0, scheme="unknown")  # type: ignore[arg-type]


# Shared span-operation arguments


def test_encode_rejects_negative_length() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        encode([], length=-1, scheme="bio")


def test_check_representability_rejects_negative_length() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        check_representability([], length=-1, scheme="bio")


@pytest.mark.parametrize("length", [True, 1.5, "2"])
def test_encode_rejects_non_integer_length(length: object) -> None:
    with pytest.raises(TypeError, match="length"):
        encode([], length=length, scheme="bio")  # type: ignore[arg-type]


@pytest.mark.parametrize("length", [True, 1.5, "2"])
def test_check_representability_rejects_non_integer_length(length: object) -> None:
    with pytest.raises(TypeError, match="length"):
        check_representability(
            [],
            length=length,  # type: ignore[arg-type]
            scheme="bio",
        )
