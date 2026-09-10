"""Boundary semantics for flat contiguous-span schemes."""

from dataclasses import dataclass

from spanwend._scheme.flat.spec import Boundary, BoundaryCondition, FlatSchemeSpec
from spanwend._span import Span


@dataclass(frozen=True, slots=True)
class _MarkerRoles:
    """Semantic roles carried by one marker in a flat declaration."""

    body: bool
    start: bool
    end: bool
    singleton: bool


@dataclass(frozen=True, slots=True)
class _FlatSemantics:
    """Semantic view of one flat scheme declaration."""

    spec: FlatSchemeSpec

    @property
    def markers(self) -> frozenset[str]:
        """Return all legal non-outside markers."""
        markers = {self.spec.body}
        if self.spec.start is not None:
            markers.add(self.spec.start.marker)
        if self.spec.end is not None:
            markers.add(self.spec.end.marker)
        if self.spec.singleton is not None:
            markers.add(self.spec.singleton)
        return frozenset(markers)

    @property
    def requires_start(self) -> bool:
        """Whether every multi-token span requires an explicit start marker."""
        return (
            self.spec.start is not None
            and self.spec.start.condition is BoundaryCondition.ALWAYS
        )

    @property
    def requires_end(self) -> bool:
        """Whether every multi-token span requires an explicit end marker."""
        return (
            self.spec.end is not None
            and self.spec.end.condition is BoundaryCondition.ALWAYS
        )

    def roles(self, marker: str) -> _MarkerRoles:
        """Return the roles assigned to one marker."""
        return _MarkerRoles(
            body=marker == self.spec.body,
            start=self.spec.start is not None and marker == self.spec.start.marker,
            end=self.spec.end is not None and marker == self.spec.end.marker,
            singleton=self.spec.singleton is not None and marker == self.spec.singleton,
        )

    def supports(self, marker: str) -> bool:
        """Whether `marker` belongs to this declaration."""
        roles = self.roles(marker)
        return roles.body or roles.start or roles.end or roles.singleton

    def can_begin(self, marker: str) -> bool:
        """Whether `marker` can begin some valid span."""
        roles = self.roles(marker)
        if roles.singleton or roles.start:
            return True
        if self.requires_start:
            return False
        if roles.body:
            return True
        if roles.end:
            return self.spec.singleton is None or roles.singleton
        return False

    def can_continue_multi(self, marker: str) -> bool:
        """Whether `marker` can continue an attempted multi-token span."""
        roles = self.roles(marker)
        return roles.body or roles.end

    def can_start_sequence(self, marker: str) -> bool:
        """Whether `marker` may occupy the first position of a valid sequence."""
        if not self.supports(marker):
            return False

        roles = self.roles(marker)
        if roles.singleton:
            return True
        if roles.start:
            return not self.is_contextual_start(marker)
        if roles.end:
            return not self.requires_start and self.spec.singleton is None
        assert roles.body
        return not self.requires_start

    def can_end_sequence(self, marker: str) -> bool:
        """Whether `marker` may occupy the final position of a valid sequence."""
        if not self.supports(marker):
            return False

        roles = self.roles(marker)
        if roles.singleton:
            return True
        if roles.end:
            return not self.is_contextual_end(marker)
        if roles.start:
            return not self.requires_end and self.spec.singleton is None
        assert roles.body
        return not self.requires_end

    def uses_start_role(self, marker: str, next_marker: str | None) -> bool:
        """Whether a start-capable marker opens a span rather than a singleton."""
        roles = self.roles(marker)
        if not roles.start:
            return False
        if not roles.singleton:
            return True
        return (
            next_marker is not None
            and self.supports(next_marker)
            and self.can_continue_multi(next_marker)
        )

    def requires_continuation_after(self, marker: str) -> bool:
        """Whether an open span ending at `marker` must consume another tag."""
        if self.requires_end:
            return True
        roles = self.roles(marker)
        return self.spec.singleton is not None and roles.start and not roles.singleton

    def is_contextual_start(self, marker: str) -> bool:
        """Whether `marker` is a start boundary required only by adjacency."""
        boundary = self.spec.start
        return (
            boundary is not None
            and marker == boundary.marker
            and boundary.condition is BoundaryCondition.ADJACENT_SAME_LABEL
        )

    def is_contextual_end(self, marker: str) -> bool:
        """Whether `marker` is an end boundary required only by adjacency."""
        boundary = self.spec.end
        return (
            boundary is not None
            and marker == boundary.marker
            and boundary.condition is BoundaryCondition.ADJACENT_SAME_LABEL
        )

    def marker_for(
        self,
        span: Span,
        index: int,
        *,
        previous: Span | None,
        next_span: Span | None,
    ) -> str:
        """Return the unique marker for one position of a representable span."""
        if span.end == span.start + 1 and self.spec.singleton is not None:
            return self.spec.singleton

        left = (
            index == span.start
            and self.spec.start is not None
            and _boundary_required(
                self.spec.start,
                adjacent=(
                    previous is not None
                    and previous.end == span.start
                    and previous.label == span.label
                ),
            )
        )
        right = (
            index == span.end - 1
            and self.spec.end is not None
            and _boundary_required(
                self.spec.end,
                adjacent=(
                    next_span is not None
                    and span.end == next_span.start
                    and next_span.label == span.label
                ),
            )
        )

        if left:
            assert self.spec.start is not None
            return self.spec.start.marker
        if right:
            assert self.spec.end is not None
            return self.spec.end.marker
        return self.spec.body

    def can_separate_adjacent_same_label(
        self,
        first: Span,
        second: Span,
    ) -> bool:
        """Whether the declaration can preserve one same-label adjacency."""
        if self.spec.start is not None or self.spec.end is not None:
            return True
        if self.spec.singleton is None:
            return False
        return first.end == first.start + 1 or second.end == second.start + 1


def _boundary_required(boundary: Boundary, *, adjacent: bool) -> bool:
    """Whether one configured boundary marker is required in context."""
    if boundary.condition is BoundaryCondition.ALWAYS:
        return True
    return adjacent
