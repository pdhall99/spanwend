"""Internal scheme metadata and codec boundary."""

from dataclasses import dataclass
from typing import Protocol

from spanwend._check import _require_non_blank_string
from spanwend._diagnostic import Diagnostic, DiagnosticCode
from spanwend._input import _NormalizedSpans, _TagSequence
from spanwend._repair import RepairPolicy
from spanwend._representability import RepresentabilityResult
from spanwend._scheme.analysis import _Analysis
from spanwend._syntax import DEFAULT_SYNTAX, TagSyntax


class SchemeCodec(Protocol):
    """Semantic operations supplied by one scheme implementation.

    The shared runtime materializes tag inputs and validates, normalizes, and orders
    span inputs before invoking a codec.
    """

    def analyze(
        self,
        tags: _TagSequence,
        *,
        syntax: TagSyntax = DEFAULT_SYNTAX,
    ) -> _Analysis:
        """Analyze one materialized encoded sequence."""
        ...

    def encode(
        self,
        spans: _NormalizedSpans,
        *,
        length: int,
        syntax: TagSyntax = DEFAULT_SYNTAX,
    ) -> _TagSequence:
        """Faithfully encode a normalized canonical span collection."""
        ...

    def check_representability(
        self,
        spans: _NormalizedSpans,
        *,
        length: int,
    ) -> RepresentabilityResult:
        """Check a normalized canonical span collection for faithful encoding."""
        ...


class RepairFunction(Protocol):
    """One policy-specific repair transformation."""

    def __call__(
        self,
        tags: _TagSequence,
        *,
        syntax: TagSyntax,
    ) -> tuple[_TagSequence, tuple[Diagnostic, ...]]:
        """Return rewritten tags and repair diagnostics for accepted input.

        Runtime checks the rule's input domain and validates the returned tags.
        """
        ...


@dataclass(frozen=True, slots=True)
class RepairRule:
    """Bind a repair policy to its accepted diagnostic codes and transformation."""

    policy: RepairPolicy
    repair: RepairFunction
    repairable_codes: frozenset[DiagnosticCode]


@dataclass(frozen=True, slots=True)
class Scheme:
    """Private metadata and runtime behaviour for one semantic scheme."""

    name: str
    aliases: tuple[str, ...]
    codec: SchemeCodec
    repairs: tuple[RepairRule, ...] = ()

    def __post_init__(self) -> None:
        """Reject ambiguous names and duplicate repair policies."""
        _require_non_blank_string(self.name, name="Scheme.name")
        seen_names = {self.name.casefold()}
        for alias in self.aliases:
            _require_non_blank_string(alias, name="Scheme.alias")
            normalized = alias.casefold()
            if normalized in seen_names:
                raise ValueError(
                    "Scheme name and aliases must be unique ignoring case; "
                    f"got {alias!r}"
                )
            seen_names.add(normalized)

        seen_policies: set[RepairPolicy] = set()
        for rule in self.repairs:
            if rule.policy in seen_policies:
                raise ValueError(
                    f"Scheme repair policies must be unique; got {rule.policy.value!r}"
                )
            seen_policies.add(rule.policy)

    def repair_rule_for(self, policy: RepairPolicy) -> RepairRule | None:
        """Return the rule for `policy`, if the scheme supports it."""
        for rule in self.repairs:
            if rule.policy is policy:
                return rule
        return None
