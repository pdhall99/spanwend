"""Conversion from flexible/raw caller input into validated canonical input."""

from collections.abc import Iterable, Mapping
from typing import TypeAlias, TypedDict, cast

from spanwend._check import _require_instance, _require_integer
from spanwend._span import Span


class _OptionalSpanLabel(TypedDict, total=False):
    label: str | None


class SpanMapping(_OptionalSpanLabel):
    """Mapping form accepted for one public span input."""

    start: int
    end: int


SpanTuple: TypeAlias = tuple[int, int] | tuple[int, int, str | None]
SpanInput: TypeAlias = Span | SpanTuple | SpanMapping

_NormalizedSpans = tuple[Span, ...]
_TagSequence = tuple[str, ...]


def _normalize_span_input(value: object, *, name: str) -> Span:
    """Convert one supported public span representation to canonical `Span`."""
    if isinstance(value, Span):
        return value

    if isinstance(value, tuple):
        if len(value) == 2:
            start, end = value
            label = None
        elif len(value) == 3:
            start, end, label = value
        else:
            raise TypeError(
                f"{name}: expected a 2- or 3-item span tuple, got {len(value)} items"
            )
        return Span(
            cast(int, start),
            cast(int, end),
            cast(str | None, label),
        )

    if isinstance(value, Mapping):
        missing = tuple(key for key in ("start", "end") if key not in value)
        if missing:
            names = ", ".join(repr(key) for key in missing)
            raise ValueError(f"{name}: span mapping missing required key(s): {names}")

        allowed = {"start", "end", "label"}
        unexpected = sorted(repr(key) for key in value if key not in allowed)
        if unexpected:
            names = ", ".join(unexpected)
            raise ValueError(f"{name}: span mapping has unsupported key(s): {names}")

        return Span(
            cast(int, value["start"]),
            cast(int, value["end"]),
            cast(str | None, value.get("label")),
        )

    raise TypeError(
        f"{name}: expected Span, a 2- or 3-item tuple, or a mapping, "
        f"got {type(value).__name__}"
    )


def _normalize_spans(spans: Iterable[object]) -> _NormalizedSpans:
    """Normalize supported public span inputs and return canonical order."""
    try:
        iterator = iter(spans)
    except TypeError as exc:
        raise TypeError(
            f"spans: expected an iterable of span inputs, got {type(spans).__name__}"
        ) from exc

    normalized: list[Span] = []
    has_labelled = False
    has_unlabelled = False
    for index, value in enumerate(iterator):
        span = _normalize_span_input(value, name=f"spans[{index}]")

        if span.label is None:
            has_unlabelled = True
        else:
            has_labelled = True

        if has_labelled and has_unlabelled:
            raise ValueError("spans: labelled and unlabelled spans cannot be mixed")
        normalized.append(span)

    return tuple(sorted(normalized, key=Span._sort_key))


def _normalize_tags(tags: Iterable[object]) -> _TagSequence:
    """Validate and materialize a tag collection."""
    if isinstance(tags, (str, bytes)):
        raise TypeError(
            f"tags: expected an iterable of tag strings, got {type(tags).__name__}"
        )

    try:
        iterator = iter(tags)
    except TypeError as exc:
        raise TypeError(
            f"tags: expected an iterable of tag strings, got {type(tags).__name__}"
        ) from exc

    normalized: list[str] = []
    for index, tag in enumerate(iterator):
        tag = _require_instance(tag, str, name=f"tags[{index}]")
        normalized.append(tag)

    return tuple(normalized)


def _normalize_length(length: object) -> int:
    normalized = _require_integer(length, name="length")
    if normalized < 0:
        raise ValueError(f"length: expected a non-negative value, got {normalized}")

    return normalized
