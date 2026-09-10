"""Tests for the canonical Span value."""

from dataclasses import FrozenInstanceError

import pytest

from spanwend import Span


def test_span_is_right_open_value() -> None:
    span = Span(2, 5, "PER")

    assert span.start == 2
    assert span.end == 5
    assert span.label == "PER"


def test_span_may_be_unlabelled() -> None:
    assert Span(2, 5, None).label is None


def test_span_is_immutable() -> None:
    span = Span(0, 1, "PER")

    with pytest.raises(FrozenInstanceError):
        span.start = 1  # type: ignore[misc]


@pytest.mark.parametrize("start", [True, 1.5, "1"])
def test_span_rejects_invalid_start_type(start: object) -> None:
    with pytest.raises(TypeError):
        Span(start, 2, "PER")  # type: ignore[arg-type]


@pytest.mark.parametrize("start", [-1])
def test_span_rejects_invalid_start_value(start: object) -> None:
    with pytest.raises(ValueError):
        Span(start, 2, "PER")  # type: ignore[arg-type]


@pytest.mark.parametrize("end", [True, 1.5, "2"])
def test_span_rejects_invalid_end_type(end: object) -> None:
    with pytest.raises(TypeError):
        Span(0, end, "PER")  # type: ignore[arg-type]


@pytest.mark.parametrize("end", [0, -1])
def test_span_rejects_invalid_end_value(end: object) -> None:
    with pytest.raises(ValueError):
        Span(0, end, "PER")  # type: ignore[arg-type]


def test_span_rejects_end_equal_to_start() -> None:
    with pytest.raises(ValueError):
        Span(2, 2, "PER")


@pytest.mark.parametrize("label", ["", " ", "\n"])
def test_span_rejects_invalid_label_value(label: object) -> None:
    with pytest.raises(ValueError):
        Span(0, 1, label)  # type: ignore[arg-type]


@pytest.mark.parametrize("label", [3])
def test_span_rejects_invalid_label_type(label: object) -> None:
    with pytest.raises(TypeError):
        Span(0, 1, label)  # type: ignore[arg-type]
