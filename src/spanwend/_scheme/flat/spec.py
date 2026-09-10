"""Declarative model for flat contiguous-span tagging schemes."""

from dataclasses import dataclass
from enum import Enum, auto

from spanwend._check import _require_instance, _require_non_blank_string


class BoundaryCondition(Enum):
    """Condition under which a flat-span boundary marker is required."""

    ALWAYS = auto()
    ADJACENT_SAME_LABEL = auto()


@dataclass(frozen=True, slots=True)
class Boundary:
    """One explicit start or end marker in a flat-span scheme."""

    marker: str
    condition: BoundaryCondition = BoundaryCondition.ALWAYS

    def __post_init__(self) -> None:
        """Validate the boundary declaration."""
        _require_marker(self.marker, field="boundary marker")
        _require_instance(self.condition, BoundaryCondition, name="boundary condition")


@dataclass(frozen=True, slots=True)
class FlatSchemeSpec:
    """Readable declaration of a flat contiguous-span tagging vocabulary."""

    body: str
    start: Boundary | None = None
    end: Boundary | None = None
    singleton: str | None = None

    def __post_init__(self) -> None:
        """Reject ambiguous marker vocabularies and boundary semantics."""
        _require_marker(self.body, field="body")
        if self.start is not None:
            _require_instance(self.start, Boundary, name="FlatSchemeSpec.start")
        if self.end is not None:
            _require_instance(self.end, Boundary, name="FlatSchemeSpec.end")
        if self.singleton is not None:
            _require_marker(self.singleton, field="FlatSchemeSpec.singleton")

        boundary_markers = [self.body]
        if self.start is not None:
            boundary_markers.append(self.start.marker)
        if self.end is not None:
            boundary_markers.append(self.end.marker)

        if len(boundary_markers) != len(set(boundary_markers)):
            raise ValueError(
                "Flat scheme body, start, and end markers must be distinct; "
                f"got {', '.join(repr(marker) for marker in boundary_markers)}"
            )

        if self.singleton == self.body:
            raise ValueError(
                "Flat scheme singleton marker must differ from the body marker"
            )

        if self.start is not None and self.end is not None and self.singleton is None:
            raise ValueError(
                "Flat schemes with both start and end boundaries require a singleton "
                "override"
            )


def _require_marker(value: str, *, field: str) -> None:
    """Require a valid marker in the flat scheme language."""
    _require_non_blank_string(value, name=field)
    if value == "O":
        raise ValueError(f"{field}: marker 'O' is reserved for outside tags")


def _require_supported_codec_spec(
    spec: FlatSchemeSpec,
    *,
    invalid_start_guidance: str = "",
    invalid_boundary_guidance: str = "",
) -> None:
    """Require diagnostic guidance to match the declared boundary semantics."""
    if invalid_start_guidance and spec.start is None:
        raise ValueError("Start guidance requires a declared start boundary")

    contextual = (
        spec.start is not None
        and spec.start.condition is BoundaryCondition.ADJACENT_SAME_LABEL
    ) or (
        spec.end is not None
        and spec.end.condition is BoundaryCondition.ADJACENT_SAME_LABEL
    )
    if invalid_boundary_guidance and not contextual:
        raise ValueError(
            "Boundary guidance requires an adjacent-same-label boundary condition"
        )
