"""Flat sequence analysis, diagnostic recovery, and span extraction."""

from dataclasses import dataclass

from spanwend._diagnostic import Diagnostic, DiagnosticCode
from spanwend._scheme.analysis import _Analysis, _ParsedSequence
from spanwend._scheme.flat.semantics import _FlatSemantics
from spanwend._scheme.flat.spec import BoundaryCondition, FlatSchemeSpec
from spanwend._span import Span
from spanwend._syntax import _ParsedTag


@dataclass(slots=True)
class _RecoverySpanState:
    """Open-span state used while recovering deterministic diagnostics."""

    start: int | None = None
    label: str | None = None
    initial_marker: str | None = None
    length: int = 0
    recovering: bool = False

    @property
    def open(self) -> bool:
        """Whether a span is currently open."""
        return self.start is not None

    def clear(self) -> None:
        """Reset to the outside state."""
        self.start = None
        self.label = None
        self.initial_marker = None
        self.length = 0
        self.recovering = False

    def begin(
        self,
        index: int,
        label: str,
        marker: str,
        *,
        recovering: bool = False,
    ) -> None:
        """Open a span for decoding or deterministic validation continuation."""
        self.start = index
        self.label = label
        self.initial_marker = marker
        self.length = 1
        self.recovering = recovering

    def extend(self) -> None:
        """Record one additional position in the open span."""
        self.length += 1

    def must_continue(self, semantics: _FlatSemantics) -> bool:
        """Whether closing now would leave an incomplete strict span."""
        if not self.open or self.recovering:
            return False
        if semantics.requires_end:
            return True
        return (
            semantics.spec.singleton is not None
            and self.length == 1
            and self.initial_marker != semantics.spec.singleton
        )


@dataclass(frozen=True, slots=True)
class _FlatSpanAnalyzer:
    """Analyze tags using the boundary semantics of one flat scheme."""

    semantics: _FlatSemantics
    display_name: str
    invalid_start_guidance: str = ""
    invalid_boundary_guidance: str = ""

    @property
    def spec(self) -> FlatSchemeSpec:
        """Return the underlying flat declaration."""
        return self.semantics.spec

    def analyze_parsed(self, sequence: _ParsedSequence) -> _Analysis:
        """Analyze an already parsed sequence from shared boundary semantics."""
        state = _RecoverySpanState()
        spans: list[Span] = []
        diagnostics: list[Diagnostic] = []

        def close(end: int) -> None:
            if state.start is None or state.label is None:
                return
            spans.append(Span(state.start, end, state.label))
            state.clear()

        def append_singleton(index: int, label: str) -> None:
            spans.append(Span(index, index + 1, label))

        def previous_span_matches(index: int, label: str) -> bool:
            return bool(spans) and spans[-1].end == index and spans[-1].label == label

        for index, tag in enumerate(sequence.parsed_tags):
            if tag is None:
                if state.open:
                    if state.must_continue(self.semantics):
                        self._append_unterminated(
                            sequence,
                            diagnostics,
                            state,
                            index=index,
                            interrupted=True,
                        )
                    close(index)
                continue

            if tag.marker == "O":
                self._append_outside_label_diagnostic(
                    sequence,
                    diagnostics,
                    index=index,
                    label=tag.label,
                )
                if state.open:
                    if state.must_continue(self.semantics):
                        self._append_invalid_transition(
                            sequence,
                            diagnostics,
                            state,
                            index=index,
                        )
                    close(index)
                continue

            if not self.semantics.supports(tag.marker):
                diagnostics.append(
                    sequence.diagnostic(
                        DiagnosticCode.UNSUPPORTED_MARKER,
                        index,
                        self._unsupported_marker_message(
                            tag.marker,
                            sequence=sequence,
                        ),
                    )
                )
                if state.open:
                    if state.must_continue(self.semantics):
                        self._append_invalid_transition(
                            sequence,
                            diagnostics,
                            state,
                            index=index,
                        )
                    close(index)
                continue

            assert tag.label is not None
            roles = self.semantics.roles(tag.marker)

            if not state.open:
                if (
                    roles.singleton
                    and roles.start
                    and self._begins_multi_attempt(
                        sequence,
                        index,
                    )
                ):
                    state.begin(index, tag.label, tag.marker)
                    continue

                if roles.singleton:
                    append_singleton(index, tag.label)
                    continue

                if roles.start:
                    assert self.spec.start is not None
                    if (
                        self.spec.start.condition
                        is BoundaryCondition.ADJACENT_SAME_LABEL
                        and not previous_span_matches(index, tag.label)
                    ):
                        self._append_invalid_boundary(
                            sequence,
                            diagnostics,
                            index=index,
                            side="start",
                        )
                    state.begin(index, tag.label, tag.marker)
                    continue

                if roles.end:
                    assert self.spec.end is not None
                    if (
                        self.spec.end.condition is BoundaryCondition.ADJACENT_SAME_LABEL
                        and not self._next_starts_same_label(
                            sequence,
                            index,
                            tag.label,
                        )
                    ):
                        self._append_invalid_boundary(
                            sequence,
                            diagnostics,
                            index=index,
                            side="end",
                        )

                    if (
                        not self.semantics.requires_start
                        and self.spec.singleton is None
                    ):
                        append_singleton(index, tag.label)
                    else:
                        self._append_invalid_start(
                            sequence,
                            diagnostics,
                            index=index,
                        )
                    continue

                assert roles.body
                if self.semantics.requires_start:
                    self._append_invalid_start(
                        sequence,
                        diagnostics,
                        index=index,
                    )
                    state.begin(
                        index,
                        tag.label,
                        tag.marker,
                        recovering=True,
                    )
                else:
                    state.begin(index, tag.label, tag.marker)
                continue

            if roles.start:
                assert self.spec.start is not None
                if (
                    self.spec.start.condition is BoundaryCondition.ADJACENT_SAME_LABEL
                    and state.label != tag.label
                ):
                    self._append_invalid_boundary(
                        sequence,
                        diagnostics,
                        index=index,
                        side="start",
                    )
                recovering = state.must_continue(self.semantics)
                if recovering:
                    self._append_invalid_transition(
                        sequence,
                        diagnostics,
                        state,
                        index=index,
                    )
                close(index)
                if roles.singleton and not self._begins_multi_attempt(
                    sequence,
                    index,
                ):
                    append_singleton(index, tag.label)
                else:
                    state.begin(
                        index,
                        tag.label,
                        tag.marker,
                        recovering=recovering,
                    )
                continue

            if roles.end:
                assert self.spec.end is not None
                if self.spec.end.condition is BoundaryCondition.ADJACENT_SAME_LABEL:
                    if not self._next_starts_same_label(
                        sequence,
                        index,
                        tag.label,
                    ):
                        self._append_invalid_boundary(
                            sequence,
                            diagnostics,
                            index=index,
                            side="end",
                        )

                    if state.label != tag.label:
                        if state.must_continue(self.semantics):
                            self._append_invalid_transition(
                                sequence,
                                diagnostics,
                                state,
                                index=index,
                            )
                        close(index)
                        state.begin(index, tag.label, tag.marker)
                    else:
                        state.extend()
                    close(index + 1)
                    continue

                if state.label != tag.label:
                    self._append_label_mismatch(
                        sequence,
                        diagnostics,
                        state,
                        index=index,
                        marker=tag.marker,
                    )
                    close(index)
                    if (
                        not self.semantics.requires_start
                        and self.spec.singleton is None
                    ):
                        append_singleton(index, tag.label)
                    continue

                state.extend()
                close(index + 1)
                continue

            if roles.singleton:
                if state.must_continue(self.semantics):
                    self._append_invalid_transition(
                        sequence,
                        diagnostics,
                        state,
                        index=index,
                    )
                close(index)
                append_singleton(index, tag.label)
                continue

            assert roles.body
            if state.label != tag.label:
                if self.semantics.requires_start or self.semantics.requires_end:
                    self._append_label_mismatch(
                        sequence,
                        diagnostics,
                        state,
                        index=index,
                        marker=tag.marker,
                    )
                    close(index)
                    state.begin(
                        index,
                        tag.label,
                        tag.marker,
                        recovering=True,
                    )
                else:
                    if state.must_continue(self.semantics):
                        self._append_invalid_transition(
                            sequence,
                            diagnostics,
                            state,
                            index=index,
                        )
                    close(index)
                    state.begin(index, tag.label, tag.marker)
            else:
                state.extend()

        if state.open:
            if state.must_continue(self.semantics):
                self._append_unterminated(
                    sequence,
                    diagnostics,
                    state,
                    index=len(sequence.parsed_tags) - 1,
                    interrupted=False,
                )
            close(len(sequence.parsed_tags))

        return _Analysis(tuple(spans), tuple(diagnostics))

    def _begins_multi_attempt(
        self,
        sequence: _ParsedSequence,
        index: int,
    ) -> bool:
        next_index = index + 1
        if next_index >= len(sequence.parsed_tags):
            return False
        next_tag = sequence.parsed_tags[next_index]
        return (
            next_tag is not None
            and next_tag.marker != "O"
            and self.semantics.supports(next_tag.marker)
            and self.semantics.can_continue_multi(next_tag.marker)
        )

    def _next_starts_same_label(
        self,
        sequence: _ParsedSequence,
        index: int,
        label: str,
    ) -> bool:
        next_index = index + 1
        if next_index >= len(sequence.parsed_tags):
            return False
        next_tag = sequence.parsed_tags[next_index]
        return (
            next_tag is not None
            and next_tag.marker != "O"
            and next_tag.label == label
            and self.semantics.supports(next_tag.marker)
            and self.semantics.can_begin(next_tag.marker)
        )

    def _append_invalid_start(
        self,
        sequence: _ParsedSequence,
        diagnostics: list[Diagnostic],
        *,
        index: int,
    ) -> None:
        tag = sequence.parsed_tags[index]
        assert tag is not None

        message = (
            f"{sequence.display(index)!r} cannot begin a span in {self.display_name}."
        )
        if self.spec.start is not None and self.spec.singleton is not None:
            label = sequence.syntax._parse(sequence.tags[index]).label
            start_example = self._tag_example(sequence, self.spec.start.marker, label)
            if self.semantics.roles(tag.marker).end and self.spec.end is not None:
                end_example = self._tag_example(sequence, self.spec.end.marker, label)
                message = (
                    f"{sequence.display(index)!r} cannot appear without an open span "
                    f"in {self.display_name}; a multi-token span must begin with "
                    f"{start_example} before {end_example}."
                )
            else:
                singleton_example = self._tag_example(
                    sequence, self.spec.singleton, label
                )
                message = (
                    f"{sequence.display(index)!r} cannot begin a span in "
                    f"{self.display_name}; use {start_example} for a multi-token span "
                    f"or {singleton_example} for a one-token span."
                )

        diagnostics.append(
            sequence.diagnostic(
                DiagnosticCode.INVALID_START,
                index,
                self._with_guidance(message, self.invalid_start_guidance),
            )
        )

    def _append_invalid_boundary(
        self,
        sequence: _ParsedSequence,
        diagnostics: list[Diagnostic],
        *,
        index: int,
        side: str,
    ) -> None:
        boundary = self.spec.start if side == "start" else self.spec.end
        assert boundary is not None
        position = "before" if side == "start" else "after"
        diagnostics.append(
            sequence.diagnostic(
                DiagnosticCode.INVALID_BOUNDARY,
                index,
                self._with_guidance(
                    f"{sequence.display(index)!r} is not required at this position "
                    f"in {self.display_name}; {boundary.marker} marks a boundary "
                    f"{position} this position only for adjacent spans with the "
                    "same label.",
                    self.invalid_boundary_guidance,
                ),
            )
        )

    def _append_invalid_transition(
        self,
        sequence: _ParsedSequence,
        diagnostics: list[Diagnostic],
        state: _RecoverySpanState,
        *,
        index: int,
    ) -> None:
        assert state.start is not None
        label = sequence.syntax._parse(sequence.tags[state.start]).label
        span_description = self._span_description(label)
        if self.semantics.requires_end and self.spec.end is not None:
            body_example = self._tag_example(sequence, self.spec.body, label)
            end_example = self._tag_example(sequence, self.spec.end.marker, label)
            label_guidance = " using the same label" if label is not None else ""
            message = (
                f"{sequence.display(index)!r} cannot follow the open "
                f"{span_description} in {self.display_name}; every multi-token "
                f"span must continue with {body_example} or end with {end_example}"
                f"{label_guidance}."
            )
        else:
            message = (
                f"{sequence.display(index)!r} cannot follow the open "
                f"{span_description} in {self.display_name}; the span is not "
                "complete at this boundary."
            )

        diagnostics.append(
            sequence.diagnostic(
                DiagnosticCode.INVALID_TRANSITION,
                index,
                message,
            )
        )

    def _append_label_mismatch(
        self,
        sequence: _ParsedSequence,
        diagnostics: list[Diagnostic],
        state: _RecoverySpanState,
        *,
        index: int,
        marker: str,
    ) -> None:
        assert state.start is not None
        label = sequence.syntax._parse(sequence.tags[state.start]).label
        example = self._tag_example(sequence, marker, label)
        action = "end" if self.semantics.roles(marker).end else "continue"
        diagnostics.append(
            sequence.diagnostic(
                DiagnosticCode.LABEL_MISMATCH,
                index,
                f"{sequence.display(index)!r} cannot {action} the open "
                f"{self._span_description(label)} in {self.display_name}; "
                f"{example} must match "
                "the current span label.",
            )
        )

    def _append_unterminated(
        self,
        sequence: _ParsedSequence,
        diagnostics: list[Diagnostic],
        state: _RecoverySpanState,
        *,
        index: int,
        interrupted: bool,
    ) -> None:
        assert state.start is not None
        label = sequence.syntax._parse(sequence.tags[state.start]).label
        if self.semantics.requires_end and self.spec.end is not None:
            end_example = self._tag_example(sequence, self.spec.end.marker, label)
            ending = (
                f"is interrupted before {end_example}"
                if interrupted
                else f"reaches the end of the sequence without {end_example}"
            )
        else:
            ending = (
                "is interrupted before it is complete"
                if interrupted
                else "reaches the end of the sequence before it is complete"
            )
        diagnostics.append(
            sequence.diagnostic(
                DiagnosticCode.UNTERMINATED_SPAN,
                index,
                f"The open {self._span_description(label)} in "
                f"{self.display_name} {ending}.",
            )
        )

    def _append_outside_label_diagnostic(
        self,
        sequence: _ParsedSequence,
        diagnostics: list[Diagnostic],
        *,
        index: int,
        label: str | None,
    ) -> None:
        if label is None:
            return
        diagnostics.append(
            sequence.diagnostic(
                DiagnosticCode.OUTSIDE_WITH_LABEL,
                index,
                f"The {self.display_name} outside state must use the configured "
                f"outside tag {sequence.syntax.outside!r} without label {label!r}.",
            )
        )

    def _unsupported_marker_message(
        self,
        marker: str,
        *,
        sequence: _ParsedSequence,
    ) -> str:
        expected = ", ".join(sorted(self.semantics.markers))
        return (
            f"Scheme marker {marker!r} is not valid in {self.display_name}; "
            f"expected one of {expected}, or the configured outside tag "
            f"{sequence.syntax.outside!r}."
        )

    @staticmethod
    def _tag_example(sequence: _ParsedSequence, marker: str, label: str | None) -> str:
        """Format a marker example using the source tag's syntax and label mode."""
        return sequence.syntax._format(
            _ParsedTag(marker, "LABEL" if label is not None else None)
        )

    @staticmethod
    def _span_description(label: str | None) -> str:
        return "unlabelled span" if label is None else f"{label!r} span"

    @staticmethod
    def _with_guidance(message: str, guidance: str) -> str:
        if not guidance:
            return message
        return f"{message} {guidance}"
