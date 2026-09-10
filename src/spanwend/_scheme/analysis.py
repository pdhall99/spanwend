"""Shared parsing and analysis context for built-in tagging schemes."""

from dataclasses import dataclass

from spanwend._diagnostic import Diagnostic, DiagnosticCode
from spanwend._input import _NormalizedSpans, _TagSequence
from spanwend._span import Span
from spanwend._syntax import TagSyntax, _ParsedTag, _TagParseError

_UNLABELLED_ANALYSIS_LABEL = "<unlabelled>"


@dataclass(frozen=True, slots=True)
class _ParsedSequence:
    """Materialized source sequence plus syntax-independent parsed tags."""

    tags: _TagSequence
    parsed_tags: tuple[_ParsedTag | None, ...]
    syntax: TagSyntax

    def display(self, index: int) -> str:
        """Return one tag."""
        return self.tags[index]

    def previous(self, index: int) -> str | None:
        """Return the preceding raw tag when present."""
        if index == 0:
            return None
        return self.tags[index - 1]

    def next(self, index: int) -> str | None:
        """Return the following tag when present."""
        if index + 1 >= len(self.tags):
            return None
        return self.tags[index + 1]

    def diagnostic(
        self,
        code: DiagnosticCode,
        index: int,
        message: str,
    ) -> Diagnostic:
        """Build a diagnostic with symmetric local context."""
        return Diagnostic(
            code=code,
            index=index,
            tag=self.display(index),
            message=message,
            previous_tag=self.previous(index),
            next_tag=self.next(index),
        )


@dataclass(frozen=True, slots=True)
class _Analysis:
    """Spans and diagnostics produced by scheme analysis."""

    spans: _NormalizedSpans
    diagnostics: tuple[Diagnostic, ...]


_PARSE_DIAGNOSTIC_CODES: dict[str, DiagnosticCode] = {
    "missing_separator": DiagnosticCode.TAG_MISSING_SEPARATOR,
    "blank_marker": DiagnosticCode.TAG_BLANK_MARKER,
    "blank_label": DiagnosticCode.TAG_BLANK_LABEL,
}


def _parse_sequence(
    tags: _TagSequence,
    syntax: TagSyntax,
) -> tuple[_ParsedSequence, tuple[Diagnostic, ...]]:
    """Parse all source tags once while retaining every lexical diagnostic."""
    parsed: list[_ParsedTag | None] = []
    failures: list[tuple[DiagnosticCode, str] | None] = []

    for tag in tags:
        try:
            parsed.append(syntax._parse(tag))
            failures.append(None)
        except _TagParseError as exc:
            parsed.append(None)
            failures.append((_PARSE_DIAGNOSTIC_CODES[exc.code], str(exc)))

    sequence = _ParsedSequence(tags, tuple(parsed), syntax)
    diagnostics: list[Diagnostic] = []
    for index, failure in enumerate(failures):
        if failure is None:
            continue
        code, message = failure
        diagnostics.append(sequence.diagnostic(code, index, message))

    return sequence, tuple(diagnostics)


def _prepare_label_mode(
    sequence: _ParsedSequence,
) -> tuple[
    _ParsedSequence,
    tuple[Diagnostic, ...],
    bool,
    frozenset[int],
]:
    """Validate one label mode and adapt unlabelled tags for labelled analyzers."""
    parsed = list(sequence.parsed_tags)
    diagnostics: list[Diagnostic] = []
    labelled_mode: bool | None = None
    has_unlabelled = False
    mixed_indices: set[int] = set()
    reported_mixed_mode = False

    for index, tag in enumerate(parsed):
        if tag is None or tag.marker == "O":
            continue

        labelled = tag.label is not None
        if labelled_mode is None:
            labelled_mode = labelled
        elif labelled is not labelled_mode:
            mixed_indices.add(index)
            if not reported_mixed_mode:
                actual = "labelled" if labelled else "unlabelled"
                expected = "labelled" if labelled_mode else "unlabelled"
                diagnostics.append(
                    sequence.diagnostic(
                        DiagnosticCode.MIXED_LABEL_MODE,
                        index,
                        f"{sequence.display(index)!r} is {actual}, but earlier "
                        f"non-outside tags in this sequence are {expected}; labelled "
                        "and unlabelled state tags cannot be mixed.",
                    )
                )
                reported_mixed_mode = True

        if not labelled:
            has_unlabelled = True
            parsed[index] = _ParsedTag(tag.marker, _UNLABELLED_ANALYSIS_LABEL)

    prepared = sequence
    if has_unlabelled:
        prepared = _ParsedSequence(
            sequence.tags,
            tuple(parsed),
            sequence.syntax,
        )

    return (
        prepared,
        tuple(diagnostics),
        labelled_mode is False,
        frozenset(mixed_indices),
    )


def _restore_unlabelled_spans(
    spans: _NormalizedSpans,
    *,
    unlabelled_mode: bool,
) -> _NormalizedSpans:
    """Restore canonical `None` labels after flat analysis."""
    if not unlabelled_mode:
        return spans
    return tuple(Span(span.start, span.end, None) for span in spans)
