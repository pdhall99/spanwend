"""Public operations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from spanwend._check import _require_instance
from spanwend._conformance import ConformanceResult
from spanwend._input import (
    SpanInput,
    _normalize_length,
    _normalize_spans,
    _normalize_tags,
)
from spanwend._repair import _REPAIR_POLICIES, RepairPolicy, RepairResult
from spanwend._representability import RepresentabilityResult
from spanwend._scheme.builtins.registry import _SCHEMES, _SchemeKey
from spanwend._scheme.model import Scheme
from spanwend._scheme.runtime import check_conformance as _check_conformance
from spanwend._scheme.runtime import check_representability as _check_representability
from spanwend._scheme.runtime import decode as _decode
from spanwend._scheme.runtime import encode as _encode
from spanwend._scheme.runtime import repair as _repair
from spanwend._span import Span
from spanwend._syntax import DEFAULT_SYNTAX, TagSyntax


def _get_scheme(scheme: str) -> Scheme:
    """Resolve a public scheme name to its semantic declaration."""
    _require_instance(scheme, str, name="scheme")
    name = scheme.casefold()
    if name == "iob":
        raise ValueError(
            "Scheme 'iob' is ambiguous; use 'iob1' for IOB1 or "
            "'bio'/'iob2' for BIO/IOB2"
        )

    try:
        return _SCHEMES[cast(_SchemeKey, name)]
    except KeyError as exc:
        accepted = ", ".join(sorted(_SCHEMES))
        raise ValueError(f"scheme: expected one of {accepted}, got {scheme!r}") from exc


def _get_repair_policy(policy: RepairPolicy | str) -> RepairPolicy:
    """Resolve a policy enum or accepted case-insensitive string."""
    _require_instance(policy, (RepairPolicy, str), name="policy")

    if isinstance(policy, RepairPolicy):
        return policy

    try:
        return _REPAIR_POLICIES[policy.casefold()]
    except KeyError as exc:
        accepted = ", ".join(sorted(_REPAIR_POLICIES))
        raise ValueError(f"policy: expected one of {accepted}, got {policy!r}") from exc


def decode(
    tags: Iterable[str],
    *,
    scheme: str,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> tuple[Span, ...]:
    """Decode a valid tag sequence into canonical right-open spans.

    Decoding is strict: malformed or scheme-invalid tags are not repaired.
    Returned spans are sorted in ascending `(start, end, label)` order.

    Args:
        tags: Tag strings to decode.
        scheme: Case-insensitive built-in scheme name or alias.
        syntax: Tag syntax used to parse the tags.

    Returns:
        The decoded canonical span collection.

    Raises:
        ValueError: If `scheme` cannot be resolved.
        InvalidTagSequenceError: If `tags` are invalid under `scheme` and `syntax`.

    Examples:
        ```pycon
        >>> from spanwend import decode
        >>> decode(["B-PER", "I-PER", "O", "B-ORG"], scheme="bio")
        (Span(start=0, end=2, label='PER'), Span(start=3, end=4, label='ORG'))

        ```
    """
    normalized_tags = _normalize_tags(tags)
    _require_instance(syntax, TagSyntax, name="syntax")
    return _decode(_get_scheme(scheme), normalized_tags, syntax=syntax)


def encode(
    spans: Iterable[SpanInput],
    *,
    length: int,
    scheme: str,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> tuple[str, ...]:
    """Encode spans without losing span semantics.

    Each input may be a canonical `Span`, a `(start, end)` or
    `(start, end, label)` tuple, or a mapping containing `start`, `end`, and an
    optional `label`. Inputs are normalized immediately to canonical `Span`
    objects. Input order is not meaningful, but labelled and unlabelled spans
    cannot be mixed.

    Args:
        spans: Span inputs to encode.
        length: Number of positions in the tag sequence. Must be non-negative.
        scheme: Case-insensitive built-in scheme name or alias.
        syntax: Tag syntax used to format the tags.

    Returns:
        The encoded tag sequence.

    Raises:
        ValueError: If `scheme` cannot be resolved, or if a span is invalid or the
            collection mixes labelled and unlabelled spans.
        UnrepresentableError: If `scheme` cannot represent the spans faithfully.

    Examples:
        ```pycon
        >>> from spanwend import encode
        >>> spans = [(0, 2, "PER"), (3, 4, "ORG")]
        >>> encode(spans, length=4, scheme="bio")
        ('B-PER', 'I-PER', 'O', 'B-ORG')

        ```
    """
    normalized_spans = _normalize_spans(spans)
    length = _normalize_length(length)
    _require_instance(syntax, TagSyntax, name="syntax")
    return _encode(
        _get_scheme(scheme),
        normalized_spans,
        length=length,
        syntax=syntax,
    )


def convert(
    tags: Iterable[str],
    *,
    source: str,
    target: str,
    source_syntax: TagSyntax = DEFAULT_SYNTAX,
    target_syntax: TagSyntax = DEFAULT_SYNTAX,
) -> tuple[str, ...]:
    """Convert a tag sequence through canonical span semantics.

    The source sequence is decoded strictly before the resulting spans are
    faithfully encoded with the target scheme and tag syntax.

    Args:
        tags: Source tag strings to convert.
        source: Case-insensitive source scheme name or alias.
        target: Case-insensitive target scheme name or alias.
        source_syntax: Tag syntax used to parse the source tags.
        target_syntax: Tag syntax used to format the target tags.

    Returns:
        The semantically equivalent target tag sequence.

    Raises:
        ValueError: If `source` or `target` cannot be resolved.
        InvalidTagSequenceError: If the source tags are invalid.
        UnrepresentableError: If the target cannot represent the decoded spans.

    Examples:
        ```pycon
        >>> from spanwend import convert
        >>> convert(
        ...     ["B-PER", "I-PER", "O", "B-ORG"],
        ...     source="bio",
        ...     target="bilou",
        ... )
        ('B-PER', 'L-PER', 'O', 'U-ORG')

        ```
    """
    normalized_tags = _normalize_tags(tags)
    source_scheme = _get_scheme(source)
    target_scheme = _get_scheme(target)
    _require_instance(source_syntax, TagSyntax, name="source_syntax")
    _require_instance(target_syntax, TagSyntax, name="target_syntax")

    spans = _decode(
        source_scheme,
        normalized_tags,
        syntax=source_syntax,
    )
    return _encode(
        target_scheme,
        spans,
        length=len(normalized_tags),
        syntax=target_syntax,
    )


def repair(
    tags: Iterable[str],
    *,
    scheme: str,
    policy: RepairPolicy | str,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> RepairResult:
    """Repair a tag sequence using an explicit supported policy.

    Repair is separate from strict decoding. Only diagnostics declared repairable
    by the selected scheme and policy are transformed.

    Args:
        tags: Tag strings to repair.
        scheme: Case-insensitive built-in scheme name or alias.
        policy: Named repair policy or its case-insensitive string value.
        syntax: Tag syntax used to parse and format the tags.

    Returns:
        The repaired tags, applied repair diagnostics, and change flag.

    Raises:
        ValueError: If `scheme` cannot be resolved.
        ValueError: If `policy` is unknown or unsupported.
        InvalidTagSequenceError: If the sequence contains an unrepairable problem.

    Examples:
        ```pycon
        >>> from spanwend import repair
        >>> result = repair(
        ...     ["O", "I-PER", "I-PER"],
        ...     scheme="bio",
        ...     policy="conlleval",
        ... )
        >>> result.tags
        ('O', 'B-PER', 'I-PER')
        >>> result.changed
        True

        ```
    """
    normalized_tags = _normalize_tags(tags)
    resolved_policy = _get_repair_policy(policy)
    _require_instance(syntax, TagSyntax, name="syntax")
    return _repair(
        _get_scheme(scheme),
        normalized_tags,
        policy=resolved_policy,
        syntax=syntax,
    )


def check_conformance(
    tags: Iterable[str],
    *,
    scheme: str,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> ConformanceResult:
    """Check whether a tag sequence conforms strictly to a scheme.

    Conformance checking reports all deterministic lexical and scheme-semantic
    diagnostics instead of raising `InvalidTagSequenceError`. It does not repair or
    transform the input tags.

    Args:
        tags: Tag strings to check.
        scheme: Case-insensitive built-in scheme name or alias.
        syntax: Tag syntax used to parse the tags.

    Returns:
        A result describing whether the sequence conforms and all diagnostics when
        it does not.

    Raises:
        ValueError: If `scheme` cannot be resolved.

    Examples:
        ```pycon
        >>> from spanwend import check_conformance
        >>> result = check_conformance(["I-PER", "I-PER"], scheme="bio")
        >>> result.conformant
        False
        >>> result.diagnostics[0].code.value
        'invalid_start'

        ```
    """
    normalized_tags = _normalize_tags(tags)
    _require_instance(syntax, TagSyntax, name="syntax")
    return _check_conformance(_get_scheme(scheme), normalized_tags, syntax=syntax)


def check_representability(
    spans: Iterable[SpanInput],
    *,
    length: int,
    scheme: str,
) -> RepresentabilityResult:
    """Check whether a scheme can faithfully encode spans.

    Each input may be a canonical `Span`, a `(start, end)` or
    `(start, end, label)` tuple, or a mapping containing `start`, `end`, and an
    optional `label`. Inputs are normalized immediately to canonical `Span`
    objects. Unlike `encode()`, representation loss is returned as a structured
    result rather than raised as `UnrepresentableError`.

    Args:
        spans: Span inputs to check.
        length: Number of positions in the tag sequence. Must be non-negative.
        scheme: Case-insensitive built-in scheme name or alias.

    Returns:
        A result describing whether the spans can be encoded faithfully and, when
        they cannot, a stable failure code and human-readable message.

    Raises:
        ValueError: If `scheme` cannot be resolved, or if a span is invalid or the
            collection mixes labelled and unlabelled spans.

    Examples:
        ```pycon
        >>> from spanwend import check_representability
        >>> spans = [(0, 1, "PER"), (1, 2, "PER")]
        >>> result = check_representability(spans, length=2, scheme="io")
        >>> result.representable
        False
        >>> result.code.value
        'adjacent_same_label'

        ```
    """
    normalized_spans = _normalize_spans(spans)
    length = _normalize_length(length)
    return _check_representability(
        _get_scheme(scheme),
        normalized_spans,
        length=length,
    )
