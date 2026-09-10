"""Tag syntax for sequence tags."""

from dataclasses import dataclass
from typing import Literal

from spanwend._check import (
    _is_blank_string,
    _require_instance,
    _require_non_blank_string,
)

_Placement = Literal["prefix", "suffix"]


@dataclass(frozen=True, slots=True)
class _ParsedTag:
    """Parsed semantic tag independent of tag syntax."""

    marker: str
    label: str | None


@dataclass(frozen=True, slots=True)
class TagSyntax:
    """Tag syntax used to parse and format semantic sequence tags.

    These fields control only how tags are written. They do not change the selected
    scheme or its marker semantics. The concise field names are therefore retained
    as properties of this syntax-only value.

    Attributes:
        separator: Non-blank tag-string separator between a scheme marker and label
            when a label is present.
        placement: Whether the scheme marker appears before (`"prefix"`) or after
            (`"suffix"`) the label in a tag string.
        outside: Non-blank tag string used to encode the outside state.
    """

    separator: str = "-"
    placement: _Placement = "prefix"
    outside: str = "O"

    def __post_init__(self) -> None:
        """Validate tag-syntax configuration."""
        _require_non_blank_string(self.separator, name="TagSyntax.separator")

        _require_instance(self.placement, str, name="TagSyntax.placement")
        if self.placement not in {"prefix", "suffix"}:
            raise ValueError(
                "TagSyntax.placement: expected 'prefix' or 'suffix', "
                f"got {self.placement!r}"
            )

        _require_non_blank_string(self.outside, name="TagSyntax.outside")
        if self.separator in self.outside:
            raise ValueError(
                "TagSyntax.outside: must not contain the configured separator "
                f"{self.separator!r}"
            )

    def _parse(self, tag: str) -> _ParsedTag:
        """Parse a tag string into its syntax-independent semantic components."""
        _require_instance(tag, str, name="tag")

        if tag == self.outside:
            return _ParsedTag("O", None)

        if self.separator not in tag:
            if _is_blank_string(tag):
                raise _TagParseError("blank_marker", f"Tag {tag!r} has a blank marker")
            if tag == "O":
                raise _TagParseError(
                    "missing_separator",
                    f"Tag {tag!r} is not the configured outside tag string "
                    f"{self.outside!r} and does not contain separator "
                    f"{self.separator!r}",
                )
            return _ParsedTag(tag, None)

        if self.placement == "prefix":
            marker, label = tag.split(self.separator, 1)
        else:
            label, marker = tag.rsplit(self.separator, 1)

        if _is_blank_string(marker):
            raise _TagParseError("blank_marker", f"Tag {tag!r} has a blank marker")
        if _is_blank_string(label):
            raise _TagParseError("blank_label", f"Tag {tag!r} has a blank label")

        return _ParsedTag(marker, label)

    def _format(self, tag: _ParsedTag) -> str:
        """Format a parsed semantic tag using the requested tag syntax."""
        if tag.label is None:
            if tag.marker == "O":
                return self.outside
            return tag.marker

        if self.placement == "prefix":
            return f"{tag.marker}{self.separator}{tag.label}"
        return f"{tag.label}{self.separator}{tag.marker}"

    def _format_checked(self, tag: _ParsedTag) -> str:
        """Format one tag and require lossless parsing with this tag syntax."""
        formatted = self._format(tag)

        if formatted == self.outside and tag.marker != "O":
            raise ValueError(
                f"TagSyntax.outside {self.outside!r} collides with encoded tag "
                f"{formatted!r}; choose a distinct outside tag."
            )

        try:
            parsed = self._parse(formatted)
        except _TagParseError:
            parsed = None

        if parsed != tag:
            raise ValueError(
                f"TagSyntax.separator {self.separator!r} cannot faithfully encode "
                f"scheme marker {tag.marker!r} with {self.placement!r} placement; "
                "choose a different separator."
            )

        return formatted


class _TagParseError(ValueError):
    """A tag string is lexically malformed during internal parsing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


DEFAULT_SYNTAX = TagSyntax()
"""The default tag syntax used by string-facing operations."""
