"""Explicit, auditable repair of supported malformed tag sequences."""

from dataclasses import dataclass
from enum import Enum

from spanwend._diagnostic import Diagnostic, DiagnosticCode
from spanwend._input import _TagSequence


class RepairPolicy(str, Enum):
    """Named repair conventions supported by `repair`."""

    CONLLEVAL = "conlleval"
    DISCARD = "discard"

    def __str__(self) -> str:
        """Return the canonical casefolded policy name."""
        return self.value


_REPAIR_POLICIES = {policy.value: policy for policy in RepairPolicy}


@dataclass(frozen=True, slots=True)
class RepairResult:
    """An immutable result of an explicit repair transformation.

    Attributes:
        tags: Repaired tag sequence.
        diagnostics: Diagnostics describing the applied repairs.
        changed: Whether the repaired sequence differs from the input.
    """

    tags: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    changed: bool


def _repair_diagnostic(
    tags: _TagSequence,
    *,
    index: int,
    code: DiagnosticCode,
    reason: str,
    replacement: str,
    policy: str,
) -> Diagnostic:
    """Build an auditable diagnostic for one concrete repair action."""
    previous_tag = tags[index - 1] if index > 0 else None
    next_tag = tags[index + 1] if index + 1 < len(tags) else None
    original = tags[index]
    return Diagnostic(
        code=code,
        index=index,
        tag=original,
        message=(
            f"{reason} Repair policy {policy!r} rewrote {original!r} "
            f"as {replacement!r}."
        ),
        previous_tag=previous_tag,
        next_tag=next_tag,
        replacement_tag=replacement,
    )
