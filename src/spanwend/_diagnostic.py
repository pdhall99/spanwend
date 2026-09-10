"""Structured validation diagnostics."""

from dataclasses import dataclass
from enum import Enum


class DiagnosticCode(str, Enum):
    """Tag diagnostic kind."""

    TAG_MISSING_SEPARATOR = "tag_missing_separator"
    TAG_BLANK_MARKER = "tag_blank_marker"
    TAG_BLANK_LABEL = "tag_blank_label"
    UNSUPPORTED_MARKER = "unsupported_marker"
    OUTSIDE_WITH_LABEL = "outside_with_label"
    MIXED_LABEL_MODE = "mixed_label_mode"
    INVALID_START = "invalid_start"
    INVALID_BOUNDARY = "invalid_boundary"
    INVALID_TRANSITION = "invalid_transition"
    LABEL_MISMATCH = "label_mismatch"
    UNTERMINATED_SPAN = "unterminated_span"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One deterministic tag diagnostic.

    Attributes:
        code: Stable machine-readable diagnostic kind.
        index: Zero-based token position containing the problem.
        tag: Original tag text.
        message: Human-readable explanation and, where useful, guidance.
        previous_tag: Original preceding tag text when present.
        next_tag: Original following tag text when present.
        replacement_tag: Tag text written by an applied repair, or `None` when
            no repair was applied.
    """

    code: DiagnosticCode
    index: int
    tag: str
    message: str
    previous_tag: str | None = None
    next_tag: str | None = None
    replacement_tag: str | None = None
