"""Public tag-sequence conformance check results."""

from dataclasses import dataclass

from spanwend._diagnostic import Diagnostic


@dataclass(frozen=True, slots=True)
class ConformanceResult:
    """The result of checking a tag sequence against a scheme.

    Attributes:
        diagnostics: A tuple of conformance diagnostics.
    """

    diagnostics: tuple[Diagnostic, ...]

    @property
    def conformant(self) -> bool:
        """Whether the sequence conforms strictly to the scheme."""
        return not self.diagnostics

    def __bool__(self) -> bool:
        return self.conformant
