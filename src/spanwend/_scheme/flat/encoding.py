"""Tag emission for normalized, representable flat spans."""

from spanwend._input import _NormalizedSpans
from spanwend._scheme.flat.semantics import _FlatSemantics
from spanwend._syntax import TagSyntax, _ParsedTag


def _encode_flat(
    semantics: _FlatSemantics,
    spans: _NormalizedSpans,
    *,
    length: int,
    syntax: TagSyntax,
) -> tuple[str, ...]:
    """Encode spans after the codec has checked their representability."""
    tags = [syntax.outside] * length

    for span_index, span in enumerate(spans):
        previous = spans[span_index - 1] if span_index > 0 else None
        next_span = spans[span_index + 1] if span_index + 1 < len(spans) else None

        for index in range(span.start, span.end):
            marker = semantics.marker_for(
                span,
                index,
                previous=previous,
                next_span=next_span,
            )
            tags[index] = syntax._format_checked(_ParsedTag(marker, span.label))

    return tuple(tags)
