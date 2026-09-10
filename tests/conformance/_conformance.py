"""Independent semantic reference helpers for conformance tests.

These helpers intentionally do not call spanwend's validation, decoding, encoding,
or representability implementations. They are a small executable specification used
to keep the conformance tests from becoming self-referential.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from itertools import product

from spanwend import DEFAULT_SYNTAX, Span, TagSyntax

IMPLEMENTED_SCHEMES = (
    "io",
    "iob1",
    "bio",
    "bioe",
    "bios",
    "ioe1",
    "ioe2",
    "ioes",
    "bioes",
    "bilou",
    "bmes",
    "bmeow",
)
LABELS = ("PER", "ORG")
SYNTAXES = (
    DEFAULT_SYNTAX,
    TagSyntax(placement="suffix"),
    TagSyntax(separator=":", outside="_"),
    TagSyntax(separator="|", placement="suffix", outside="NONE"),
)

SemanticTag = tuple[str, str | None]


def normalize(spans: Iterable[Span]) -> tuple[Span, ...]:
    """Return deterministic occurrence-preserving span order."""
    return tuple(sorted(spans, key=lambda span: (span.start, span.end, span.label)))


def format_tag(tag: SemanticTag, syntax: TagSyntax = DEFAULT_SYNTAX) -> str:
    """Format a semantic tag without using spanwend's formatter."""
    marker, label = tag
    if marker == "O":
        assert label is None
        return syntax.outside
    assert label is not None
    if syntax.placement == "prefix":
        return f"{marker}{syntax.separator}{label}"
    return f"{label}{syntax.separator}{marker}"


def scheme_markers(scheme: str) -> tuple[str, ...]:
    """Return the legal non-outside markers for a canonical scheme."""
    if scheme == "io":
        return ("I",)
    if scheme in {"iob1", "bio"}:
        return ("B", "I")
    if scheme == "bioe":
        return ("B", "I", "E")
    if scheme == "bios":
        return ("B", "I", "S")
    if scheme in {"ioe1", "ioe2"}:
        return ("I", "E")
    if scheme == "ioes":
        return ("I", "E", "S")
    if scheme == "bioes":
        return ("B", "I", "E", "S")
    if scheme == "bilou":
        return ("B", "I", "L", "U")
    if scheme == "bmes":
        return ("B", "M", "E", "S")
    if scheme == "bmeow":
        return ("B", "M", "E", "W")
    raise AssertionError(f"Unexpected scheme: {scheme}")


def semantic_alphabet(scheme: str) -> tuple[SemanticTag, ...]:
    """Return a small syntactically valid tag alphabet for exhaustive testing."""
    return (("O", None),) + tuple(
        (marker, label) for marker in scheme_markers(scheme) for label in LABELS
    )


def tag_sequences(
    scheme: str, max_length: int = 3
) -> Iterable[tuple[SemanticTag, ...]]:
    """Enumerate all small syntactically valid tag sequences for one scheme."""
    alphabet = semantic_alphabet(scheme)
    for length in range(max_length + 1):
        yield from product(alphabet, repeat=length)


def reference_is_valid(tags: Sequence[SemanticTag], scheme: str) -> bool:
    """Decide strict scheme validity from the independent grammar."""
    if scheme == "io":
        return True

    if scheme == "bio":
        open_label: str | None = None
        for marker, label in tags:
            if marker == "O":
                open_label = None
            elif marker == "B":
                open_label = label
            else:
                assert marker == "I"
                if open_label != label:
                    return False
        return True

    if scheme == "bioe":
        index = 0
        while index < len(tags):
            marker, label = tags[index]
            if marker == "O":
                index += 1
                continue
            if marker != "B":
                return False

            next_index = index + 1
            if next_index >= len(tags) or tags[next_index][0] not in {"I", "E"}:
                index += 1
                continue

            open_label = label
            index = next_index
            while index < len(tags):
                marker, current_label = tags[index]
                if marker == "I":
                    if current_label != open_label:
                        return False
                    index += 1
                    continue
                if marker == "E":
                    if current_label != open_label:
                        return False
                    index += 1
                    break
                return False
            else:
                return False
        return True

    if scheme == "bios":
        index = 0
        while index < len(tags):
            marker, label = tags[index]
            if marker in {"O", "S"}:
                index += 1
                continue
            if marker != "B":
                return False

            index += 1
            if index >= len(tags):
                return False
            marker, current_label = tags[index]
            if marker != "I" or current_label != label:
                return False

            index += 1
            while index < len(tags) and tags[index][0] == "I":
                if tags[index][1] != label:
                    return False
                index += 1
        return True

    if scheme == "iob1":
        previous_label: str | None = None
        for marker, label in tags:
            if marker == "O":
                previous_label = None
                continue
            if marker == "B" and previous_label != label:
                return False
            previous_label = label
        return True

    if scheme == "ioe1":
        for index, (marker, label) in enumerate(tags):
            if marker != "E":
                continue
            if index + 1 == len(tags):
                return False
            next_marker, next_label = tags[index + 1]
            if next_marker == "O" or next_label != label:
                return False
        return True

    if scheme == "ioe2":
        open_label: str | None = None
        for marker, label in tags:
            if open_label is None:
                if marker == "O" or marker == "E":
                    continue
                assert marker == "I"
                open_label = label
                continue

            if marker == "I" and label == open_label:
                continue
            if marker == "E" and label == open_label:
                open_label = None
                continue
            return False
        return open_label is None

    if scheme == "ioes":
        open_label: str | None = None
        for marker, label in tags:
            if open_label is None:
                if marker == "O" or marker == "S":
                    continue
                if marker == "I":
                    open_label = label
                    continue
                return False

            if marker == "I" and label == open_label:
                continue
            if marker == "E" and label == open_label:
                open_label = None
                continue
            return False
        return open_label is None

    if scheme in {"bioes", "bilou", "bmes", "bmeow"}:
        inside_marker, end_marker, single_marker = {
            "bioes": ("I", "E", "S"),
            "bilou": ("I", "L", "U"),
            "bmes": ("M", "E", "S"),
            "bmeow": ("M", "E", "W"),
        }[scheme]
        open_label: str | None = None
        for marker, label in tags:
            if open_label is None:
                if marker == "O" or marker == single_marker:
                    continue
                if marker == "B":
                    open_label = label
                    continue
                return False

            if marker == inside_marker and label == open_label:
                continue
            if marker == end_marker and label == open_label:
                open_label = None
                continue
            return False
        return open_label is None

    raise AssertionError(f"Unexpected scheme: {scheme}")


def reference_decode(tags: Sequence[SemanticTag], scheme: str) -> tuple[Span, ...]:
    """Decode a strict-valid sequence using independent scheme semantics."""
    assert reference_is_valid(tags, scheme)
    spans: list[Span] = []

    if scheme == "io":
        start: int | None = None
        label: str | None = None
        for index, (marker, current_label) in enumerate(tags):
            if marker == "O":
                if start is not None:
                    assert label is not None
                    spans.append(Span(start, index, label))
                    start = None
                    label = None
                continue
            assert current_label is not None
            if start is None:
                start = index
                label = current_label
            elif current_label != label:
                assert label is not None
                spans.append(Span(start, index, label))
                start = index
                label = current_label
        if start is not None:
            assert label is not None
            spans.append(Span(start, len(tags), label))
        return normalize(spans)

    if scheme == "bio":
        start: int | None = None
        label: str | None = None
        for index, (marker, current_label) in enumerate(tags):
            if marker == "B":
                if start is not None:
                    assert label is not None
                    spans.append(Span(start, index, label))
                start = index
                label = current_label
            elif marker == "O":
                if start is not None:
                    assert label is not None
                    spans.append(Span(start, index, label))
                    start = None
                    label = None
        if start is not None:
            assert label is not None
            spans.append(Span(start, len(tags), label))
        return normalize(spans)

    if scheme == "bioe":
        index = 0
        while index < len(tags):
            marker, label = tags[index]
            if marker == "O":
                index += 1
                continue
            assert marker == "B" and label is not None

            next_index = index + 1
            if next_index >= len(tags) or tags[next_index][0] not in {"I", "E"}:
                spans.append(Span(index, index + 1, label))
                index += 1
                continue

            end_index = next_index
            while tags[end_index][0] == "I":
                assert tags[end_index][1] == label
                end_index += 1
            assert tags[end_index] == ("E", label)
            spans.append(Span(index, end_index + 1, label))
            index = end_index + 1
        return normalize(spans)

    if scheme == "bios":
        index = 0
        while index < len(tags):
            marker, label = tags[index]
            if marker == "O":
                index += 1
                continue
            if marker == "S":
                assert label is not None
                spans.append(Span(index, index + 1, label))
                index += 1
                continue

            assert marker == "B" and label is not None
            start = index
            index += 1
            assert index < len(tags) and tags[index] == ("I", label)
            index += 1
            while index < len(tags) and tags[index][0] == "I":
                assert tags[index][1] == label
                index += 1
            spans.append(Span(start, index, label))
        return normalize(spans)

    if scheme == "iob1":
        start: int | None = None
        label: str | None = None
        for index, (marker, current_label) in enumerate(tags):
            if marker == "O":
                if start is not None:
                    assert label is not None
                    spans.append(Span(start, index, label))
                    start = None
                    label = None
                continue
            assert current_label is not None
            if start is None:
                start = index
                label = current_label
            elif marker == "B" or current_label != label:
                assert label is not None
                spans.append(Span(start, index, label))
                start = index
                label = current_label
        if start is not None:
            assert label is not None
            spans.append(Span(start, len(tags), label))
        return normalize(spans)

    if scheme == "ioe1":
        start: int | None = None
        label: str | None = None
        for index, (marker, current_label) in enumerate(tags):
            if marker == "O":
                if start is not None:
                    assert label is not None
                    spans.append(Span(start, index, label))
                    start = None
                    label = None
                continue
            assert current_label is not None
            if start is None:
                start = index
                label = current_label
            elif current_label != label:
                assert label is not None
                spans.append(Span(start, index, label))
                start = index
                label = current_label
            if marker == "E":
                assert start is not None and label is not None
                spans.append(Span(start, index + 1, label))
                start = None
                label = None
        if start is not None:
            assert label is not None
            spans.append(Span(start, len(tags), label))
        return normalize(spans)

    if scheme == "ioe2":
        start: int | None = None
        label: str | None = None
        for index, (marker, current_label) in enumerate(tags):
            if marker == "I" and start is None:
                start = index
                label = current_label
            elif marker == "E":
                assert current_label is not None
                if start is None:
                    spans.append(Span(index, index + 1, current_label))
                else:
                    assert label is not None and label == current_label
                    spans.append(Span(start, index + 1, label))
                    start = None
                    label = None
        assert start is None
        return normalize(spans)

    if scheme == "ioes":
        start: int | None = None
        label: str | None = None
        for index, (marker, current_label) in enumerate(tags):
            if marker == "S":
                assert current_label is not None
                spans.append(Span(index, index + 1, current_label))
            elif marker == "I" and start is None:
                start = index
                label = current_label
            elif marker == "E":
                assert start is not None and label is not None
                assert current_label == label
                spans.append(Span(start, index + 1, label))
                start = None
                label = None
        assert start is None
        return normalize(spans)

    inside_marker, end_marker, single_marker = {
        "bioes": ("I", "E", "S"),
        "bilou": ("I", "L", "U"),
        "bmes": ("M", "E", "S"),
        "bmeow": ("M", "E", "W"),
    }[scheme]
    start: int | None = None
    label: str | None = None
    for index, (marker, current_label) in enumerate(tags):
        if marker == "B":
            start = index
            label = current_label
        elif marker == inside_marker:
            assert start is not None and current_label == label
        elif marker == end_marker:
            assert start is not None and label is not None
            spans.append(Span(start, index + 1, label))
            start = None
            label = None
        elif marker == single_marker:
            assert current_label is not None
            spans.append(Span(index, index + 1, current_label))
    assert start is None
    return normalize(spans)


def span_collections(length: int) -> Iterable[tuple[Span, ...]]:
    """Enumerate small span occurrence collections, including duplicates/overlap."""
    candidates = tuple(
        Span(start, end, label)
        for start in range(length)
        for end in range(start + 1, length + 1)
        for label in LABELS
    )
    yield ()
    yield from ((span,) for span in candidates)
    yield from product(candidates, repeat=2)


def reference_representability_issue(
    spans: Iterable[Span], *, length: int, scheme: str
) -> str | None:
    """Return the first independent representability failure category."""
    ordered = normalize(spans)
    seen: set[Span] = set()
    for span in ordered:
        if span in seen:
            return "duplicate"
        seen.add(span)
        if span.end > length:
            return "out_of_bounds"

    previous: Span | None = None
    for span in ordered:
        if previous is not None:
            if span.start < previous.end:
                return "overlap"
            if (
                scheme == "io"
                and span.start == previous.end
                and span.label == previous.label
            ):
                return "io_adjacent_same_label"
        previous = span
    return None


def reference_is_representable(
    spans: Iterable[Span], *, length: int, scheme: str
) -> bool:
    """Decide representability without calling the public oracle or encoder."""
    return reference_representability_issue(spans, length=length, scheme=scheme) is None


def reference_encode(
    spans: Iterable[Span],
    *,
    length: int,
    scheme: str,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> tuple[str, ...]:
    """Emit the unique strict-valid representation from the independent rules."""
    ordered = normalize(spans)
    assert reference_is_representable(ordered, length=length, scheme=scheme)
    semantic: list[SemanticTag] = [("O", None)] * length

    if scheme == "io":
        for span in ordered:
            for index in range(span.start, span.end):
                semantic[index] = ("I", span.label)

    elif scheme == "bio":
        for span in ordered:
            semantic[span.start] = ("B", span.label)
            for index in range(span.start + 1, span.end):
                semantic[index] = ("I", span.label)

    elif scheme == "bioe":
        for span in ordered:
            semantic[span.start] = ("B", span.label)
            if span.end == span.start + 1:
                continue
            for index in range(span.start + 1, span.end - 1):
                semantic[index] = ("I", span.label)
            semantic[span.end - 1] = ("E", span.label)

    elif scheme == "bios":
        for span in ordered:
            if span.end == span.start + 1:
                semantic[span.start] = ("S", span.label)
                continue
            semantic[span.start] = ("B", span.label)
            for index in range(span.start + 1, span.end):
                semantic[index] = ("I", span.label)

    elif scheme == "iob1":
        previous: Span | None = None
        for span in ordered:
            first = (
                "B"
                if previous is not None
                and previous.end == span.start
                and previous.label == span.label
                else "I"
            )
            semantic[span.start] = (first, span.label)
            for index in range(span.start + 1, span.end):
                semantic[index] = ("I", span.label)
            previous = span

    elif scheme == "ioe1":
        for span_index, span in enumerate(ordered):
            next_span = (
                ordered[span_index + 1] if span_index + 1 < len(ordered) else None
            )
            boundary = (
                next_span is not None
                and span.end == next_span.start
                and span.label == next_span.label
            )
            for index in range(span.start, span.end):
                marker = "E" if boundary and index == span.end - 1 else "I"
                semantic[index] = (marker, span.label)

    elif scheme == "ioe2":
        for span in ordered:
            for index in range(span.start, span.end):
                marker = "E" if index == span.end - 1 else "I"
                semantic[index] = (marker, span.label)

    elif scheme == "ioes":
        for span in ordered:
            if span.end == span.start + 1:
                semantic[span.start] = ("S", span.label)
                continue
            for index in range(span.start, span.end):
                marker = "E" if index == span.end - 1 else "I"
                semantic[index] = (marker, span.label)

    else:
        inside_marker, end_marker, single_marker = {
            "bioes": ("I", "E", "S"),
            "bilou": ("I", "L", "U"),
            "bmes": ("M", "E", "S"),
            "bmeow": ("M", "E", "W"),
        }[scheme]
        for span in ordered:
            if span.end == span.start + 1:
                semantic[span.start] = (single_marker, span.label)
                continue
            semantic[span.start] = ("B", span.label)
            for index in range(span.start + 1, span.end - 1):
                semantic[index] = (inside_marker, span.label)
            semantic[span.end - 1] = (end_marker, span.label)

    return tuple(format_tag(tag, syntax) for tag in semantic)
