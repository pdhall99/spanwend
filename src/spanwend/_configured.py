"""Configured public scheme façade."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from spanwend._api import _get_scheme
from spanwend._api import check_conformance as _check_conformance
from spanwend._api import check_representability as _check_representability
from spanwend._api import convert as _convert
from spanwend._api import decode as _decode
from spanwend._api import encode as _encode
from spanwend._api import repair as _repair
from spanwend._check import _require_instance
from spanwend._conformance import ConformanceResult
from spanwend._input import SpanInput
from spanwend._repair import RepairPolicy, RepairResult
from spanwend._representability import RepresentabilityResult
from spanwend._span import Span
from spanwend._syntax import DEFAULT_SYNTAX, TagSyntax


@dataclass(frozen=True, slots=True)
class ConfiguredScheme:
    """Bind one built-in scheme to a tag syntax for repeated public operations.

    The façade delegates to the existing top-level public operations, preserving
    their normalization, conformance, repair, and representability contracts.

    Attributes:
        name: Canonical built-in scheme name.
        syntax: Tag syntax used by string-facing operations.
    """

    name: str
    syntax: TagSyntax = DEFAULT_SYNTAX

    def __post_init__(self) -> None:
        """Canonicalize aliases and validate direct syntax construction."""
        _require_instance(self.syntax, TagSyntax, name="ConfiguredScheme.syntax")

        resolved = _get_scheme(self.name)
        object.__setattr__(self, "name", resolved.name)

    def decode(self, tags: Iterable[str]) -> tuple[Span, ...]:
        """Decode a conformant tag sequence using this scheme and tag syntax."""
        return _decode(tags, scheme=self.name, syntax=self.syntax)

    def encode(
        self,
        spans: Iterable[SpanInput],
        *,
        length: int,
    ) -> tuple[str, ...]:
        """Faithfully encode spans using this scheme and tag syntax."""
        return _encode(spans, length=length, scheme=self.name, syntax=self.syntax)

    def convert(
        self,
        tags: Iterable[str],
        *,
        target: str | ConfiguredScheme,
    ) -> tuple[str, ...]:
        """Convert tags from this configured scheme to a target scheme.

        A string target uses the default tag syntax. A `ConfiguredScheme` target
        carries its own tag syntax.
        """
        if isinstance(target, ConfiguredScheme):
            target_name = target.name
            target_syntax = target.syntax
        else:
            target_name = target
            target_syntax = DEFAULT_SYNTAX

        return _convert(
            tags,
            source=self.name,
            target=target_name,
            source_syntax=self.syntax,
            target_syntax=target_syntax,
        )

    def repair(
        self,
        tags: Iterable[str],
        *,
        policy: RepairPolicy | str,
    ) -> RepairResult:
        """Repair tags using this scheme, tag syntax, and an explicit policy."""
        return _repair(tags, scheme=self.name, policy=policy, syntax=self.syntax)

    def check_conformance(self, tags: Iterable[str]) -> ConformanceResult:
        """Check whether tags conform to this scheme and tag syntax."""
        return _check_conformance(tags, scheme=self.name, syntax=self.syntax)

    def check_representability(
        self,
        spans: Iterable[SpanInput],
        *,
        length: int,
    ) -> RepresentabilityResult:
        """Check whether this scheme can faithfully encode the spans.

        Representability is semantic and therefore independent of configured tag
        syntax.
        """
        return _check_representability(spans, length=length, scheme=self.name)


def scheme(
    name: str,
    *,
    separator: str = DEFAULT_SYNTAX.separator,
    placement: Literal["prefix", "suffix"] = DEFAULT_SYNTAX.placement,
    outside: str = DEFAULT_SYNTAX.outside,
) -> ConfiguredScheme:
    """Return an immutable configured view of one built-in tagging scheme.

    Scheme names and aliases use the same case-insensitive resolution as the
    top-level public operations. The returned object's `name` is canonicalized.
    The remaining arguments configure only the scheme's tag syntax; they do not
    define or alter scheme semantics.

    Args:
        name: Built-in scheme name or alias.
        separator: Tag-string separator between a scheme marker and label when a
            label is present.
        placement: Whether the scheme marker appears before or after the label in a
            tag string.
        outside: Tag string used to encode the outside state.

    Returns:
        A configured scheme façade for repeated operations.

    Raises:
        ValueError: If `name` cannot be resolved.
        ValueError: If the tag-syntax configuration is invalid.

    Examples:
        ```pycon
        >>> from spanwend import scheme
        >>> bio = scheme("bio", separator=":", placement="suffix", outside="_")
        >>> bio.decode(["PER:B", "PER:I", "_"])
        (Span(start=0, end=2, label='PER'),)

        ```
    """
    return ConfiguredScheme(
        name=name,
        syntax=TagSyntax(
            separator=separator,
            placement=placement,
            outside=outside,
        ),
    )
