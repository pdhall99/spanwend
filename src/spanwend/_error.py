"""Public exception hierarchy for spanwend."""

from __future__ import annotations

from collections.abc import Iterable

from spanwend._diagnostic import Diagnostic
from spanwend._representability import RepresentabilityCode


class SpanwendError(Exception):
    """An error reported by spanwend."""


class InvalidTagSequenceError(SpanwendError, ValueError):
    """A tag sequence does not conform to the scheme required by an operation.

    Attributes:
        diagnostics: Complete deterministic diagnostics produced by the same
            analysis used by [`check_conformance`][spanwend.check_conformance].
    """

    diagnostics: tuple[Diagnostic, ...]

    def __init__(self, diagnostics: Iterable[Diagnostic]) -> None:
        self.diagnostics = tuple(diagnostics)
        if not self.diagnostics:
            raise ValueError("InvalidTagSequenceError requires at least one diagnostic")

        first = self.diagnostics[0]
        count = len(self.diagnostics)
        noun = "diagnostic" if count == 1 else "diagnostics"
        super().__init__(
            f"Invalid tag sequence: {count} {noun}; first at index "
            f"{first.index}: {first.message}"
        )

    def __reduce__(
        self,
    ) -> tuple[type[InvalidTagSequenceError], tuple[tuple[Diagnostic, ...]]]:
        """Preserve structured diagnostics when reconstructing the exception."""
        return type(self), (self.diagnostics,)


class UnrepresentableError(SpanwendError, ValueError):
    """Spans cannot be represented faithfully by a scheme.

    Attributes:
        code: Stable machine-readable reason the spans cannot be encoded.
        message: Human-readable explanation of the representation loss.
    """

    code: RepresentabilityCode
    message: str

    def __init__(self, code: RepresentabilityCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)

    def __reduce__(
        self,
    ) -> tuple[type[UnrepresentableError], tuple[RepresentabilityCode, str]]:
        """Preserve the failure code and message when reconstructing the exception."""
        return type(self), (self.code, self.message)
