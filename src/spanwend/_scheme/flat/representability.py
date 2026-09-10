"""Representability checks shared by flat contiguous-span codecs."""

from spanwend._input import _NormalizedSpans
from spanwend._representability import RepresentabilityCode, RepresentabilityResult
from spanwend._scheme.flat.semantics import _FlatSemantics
from spanwend._span import Span


def _check_flat_representability(
    spans: _NormalizedSpans,
    *,
    length: int,
    semantics: _FlatSemantics,
) -> RepresentabilityResult:
    """Apply loss constraints imposed by one flat single tag layer."""
    seen: set[Span] = set()
    for span in spans:
        if span in seen:
            return RepresentabilityResult(
                code=RepresentabilityCode.DUPLICATE_SPAN,
                message=(
                    f"Duplicate span occurrence {span!r} cannot be represented in a "
                    "single tag layer."
                ),
            )
        seen.add(span)

        if span.end > length:
            return RepresentabilityResult(
                code=RepresentabilityCode.SPAN_OUT_OF_BOUNDS,
                message=(
                    f"Span {span!r} extends beyond declared sequence length {length}."
                ),
            )

    previous: Span | None = None
    for span in spans:
        if previous is not None and span.start < previous.end:
            return RepresentabilityResult(
                code=RepresentabilityCode.OVERLAPPING_SPANS,
                message=(
                    f"Overlapping spans {previous!r} and {span!r} cannot be "
                    "represented in a single tag layer."
                ),
            )

        if (
            previous is not None
            and span.start == previous.end
            and span.label == previous.label
            and not semantics.can_separate_adjacent_same_label(previous, span)
        ):
            return RepresentabilityResult(
                code=RepresentabilityCode.ADJACENT_SAME_LABEL,
                message=(
                    "This flat tagging vocabulary cannot distinguish adjacent spans "
                    f"with the same label: {previous!r} and {span!r}."
                ),
            )
        previous = span

    return RepresentabilityResult()
