"""Public representability check results."""

from dataclasses import dataclass
from enum import Enum


class RepresentabilityCode(str, Enum):
    """Reason that span cannot be encoded faithfully."""

    DUPLICATE_SPAN = "duplicate_span"
    SPAN_OUT_OF_BOUNDS = "span_out_of_bounds"
    OVERLAPPING_SPANS = "overlapping_spans"
    ADJACENT_SAME_LABEL = "adjacent_same_label"


@dataclass(frozen=True, slots=True)
class RepresentabilityResult:
    """The result of checking whether a scheme can faithfully encode spans.

    Successful results have no `code` or `message`. Failed results expose a stable
    machine-readable `code` and a human-readable `message` describing the first
    representation loss found.

    Attributes:
        code: Stable failure kind, or `None` when the spans are representable.
        message: Human-readable failure explanation, or `None` when representable.
    """

    code: RepresentabilityCode | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        """Require failure code and message to be present or absent together."""
        if (self.code is None) != (self.message is None):
            raise ValueError(
                "RepresentabilityResult.code and message must be provided together"
            )

    @property
    def representable(self) -> bool:
        """Whether the scheme can faithfully encode the spans."""
        return self.code is None

    def __bool__(self) -> bool:
        return self.representable
