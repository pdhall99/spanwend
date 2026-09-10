"""Shared runtime lifecycle over scheme metadata and codecs."""

from spanwend._conformance import ConformanceResult
from spanwend._error import InvalidTagSequenceError
from spanwend._input import _NormalizedSpans, _TagSequence
from spanwend._repair import RepairPolicy, RepairResult
from spanwend._representability import RepresentabilityResult
from spanwend._scheme.analysis import _Analysis
from spanwend._scheme.model import Scheme
from spanwend._syntax import DEFAULT_SYNTAX, TagSyntax


def analyze(
    scheme: Scheme,
    tags: _TagSequence,
    *,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> _Analysis:
    """Run the scheme codec's complete lexical and semantic analysis."""
    return scheme.codec.analyze(tags, syntax=syntax)


def check_conformance(
    scheme: Scheme,
    tags: _TagSequence,
    *,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> ConformanceResult:
    """Check whether tags conform strictly to a scheme without repairing them."""
    return ConformanceResult(analyze(scheme, tags, syntax=syntax).diagnostics)


def decode(
    scheme: Scheme,
    tags: _TagSequence,
    *,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> _NormalizedSpans:
    """Strictly decode tags using one scheme."""
    result = analyze(scheme, tags, syntax=syntax)
    if result.diagnostics:
        raise InvalidTagSequenceError(result.diagnostics)
    return result.spans


def encode(
    scheme: Scheme,
    spans: _NormalizedSpans,
    *,
    length: int,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> _TagSequence:
    """Faithfully encode spans through the scheme codec."""
    return scheme.codec.encode(spans, length=length, syntax=syntax)


def check_representability(
    scheme: Scheme,
    spans: _NormalizedSpans,
    *,
    length: int,
) -> RepresentabilityResult:
    """Check whether the scheme codec can represent the spans faithfully."""
    return scheme.codec.check_representability(
        spans,
        length=length,
    )


def repair(
    scheme: Scheme,
    tags: _TagSequence,
    *,
    policy: RepairPolicy,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> RepairResult:
    """Check input, apply a declared repair rule, and check its output."""
    rule = scheme.repair_rule_for(policy)
    if rule is None:
        if not scheme.repairs:
            raise ValueError(
                f"Repair policy {policy.value!r} is not supported for scheme "
                f"{scheme.name!r}; scheme {scheme.name!r} has no supported "
                "repair policies."
            )
        raise ValueError(
            f"Repair policy {policy.value!r} is not supported for scheme "
            f"{scheme.name!r}."
        )

    result = check_conformance(scheme, tags, syntax=syntax)
    if any(
        diagnostic.code not in rule.repairable_codes
        for diagnostic in result.diagnostics
    ):
        raise InvalidTagSequenceError(result.diagnostics)

    repaired_tags, diagnostics = rule.repair(tags, syntax=syntax)
    if not check_conformance(scheme, repaired_tags, syntax=syntax).conformant:
        raise RuntimeError(
            "Internal repair error: supported repair policy produced a "
            f"non-conformant {scheme.name!r} sequence"
        )
    return RepairResult(
        tags=repaired_tags,
        diagnostics=diagnostics,
        changed=repaired_tags != tags,
    )
