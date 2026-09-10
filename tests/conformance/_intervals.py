"""Independent Allen-relation span-pair generation for conformance tests."""

from dataclasses import dataclass
from enum import Enum
from itertools import product

from spanwend import Span


class IntervalRelation(Enum):
    """Allen relation between two non-empty right-open intervals."""

    BEFORE = "before"
    MEETS = "meets"
    OVERLAPS = "overlaps"
    STARTS = "starts"
    DURING = "during"
    FINISHES = "finishes"
    EQUALS = "equals"
    AFTER = "after"
    MET_BY = "met_by"
    OVERLAPPED_BY = "overlapped_by"
    STARTED_BY = "started_by"
    CONTAINS = "contains"
    FINISHED_BY = "finished_by"


class SpanPairIssue(Enum):
    """Independent representability failure category for a span pair."""

    DUPLICATE = "duplicate"
    OVERLAP = "overlap"
    ADJACENT_SAME_LABEL = "adjacent_same_label"


@dataclass(frozen=True, slots=True)
class SpanPairCase:
    """One canonical feasible Allen relation, label, and extent combination."""

    relation: IntervalRelation
    same_label: bool
    first_singleton: bool
    second_singleton: bool
    spans: tuple[Span, Span]
    length: int

    @property
    def case_id(self) -> str:
        """Return a stable readable pytest parameter identifier."""
        label_relation = "same" if self.same_label else "different"
        first_extent = "singleton" if self.first_singleton else "multi"
        second_extent = "singleton" if self.second_singleton else "multi"
        return f"{self.relation.value}-{label_relation}-{first_extent}-{second_extent}"


_SINGLETON = True
_MULTI = False

# Canonical minimal coordinate realizations for the seven forward/self relations.
# Inverse relations are constructed by swapping the two intervals, which keeps the
# feasibility rules explicit without duplicating the geometry table.
_FORWARD_GEOMETRY: dict[
    tuple[IntervalRelation, bool, bool], tuple[int, int, int, int]
] = {
    (IntervalRelation.BEFORE, _SINGLETON, _SINGLETON): (0, 1, 2, 3),
    (IntervalRelation.BEFORE, _SINGLETON, _MULTI): (0, 1, 2, 4),
    (IntervalRelation.BEFORE, _MULTI, _SINGLETON): (0, 2, 3, 4),
    (IntervalRelation.BEFORE, _MULTI, _MULTI): (0, 2, 3, 5),
    (IntervalRelation.MEETS, _SINGLETON, _SINGLETON): (0, 1, 1, 2),
    (IntervalRelation.MEETS, _SINGLETON, _MULTI): (0, 1, 1, 3),
    (IntervalRelation.MEETS, _MULTI, _SINGLETON): (0, 2, 2, 3),
    (IntervalRelation.MEETS, _MULTI, _MULTI): (0, 2, 2, 4),
    (IntervalRelation.OVERLAPS, _MULTI, _MULTI): (0, 2, 1, 3),
    (IntervalRelation.STARTS, _SINGLETON, _MULTI): (0, 1, 0, 2),
    (IntervalRelation.STARTS, _MULTI, _MULTI): (0, 2, 0, 3),
    (IntervalRelation.DURING, _SINGLETON, _MULTI): (1, 2, 0, 3),
    (IntervalRelation.DURING, _MULTI, _MULTI): (1, 3, 0, 4),
    (IntervalRelation.FINISHES, _SINGLETON, _MULTI): (1, 2, 0, 2),
    (IntervalRelation.FINISHES, _MULTI, _MULTI): (1, 3, 0, 3),
    (IntervalRelation.EQUALS, _SINGLETON, _SINGLETON): (0, 1, 0, 1),
    (IntervalRelation.EQUALS, _MULTI, _MULTI): (0, 2, 0, 2),
}

_INVERSE_SOURCE: dict[IntervalRelation, IntervalRelation] = {
    IntervalRelation.AFTER: IntervalRelation.BEFORE,
    IntervalRelation.MET_BY: IntervalRelation.MEETS,
    IntervalRelation.OVERLAPPED_BY: IntervalRelation.OVERLAPS,
    IntervalRelation.STARTED_BY: IntervalRelation.STARTS,
    IntervalRelation.CONTAINS: IntervalRelation.DURING,
    IntervalRelation.FINISHED_BY: IntervalRelation.FINISHES,
}

_FLAT_GEOMETRIC_RELATIONS = {
    IntervalRelation.BEFORE,
    IntervalRelation.AFTER,
    IntervalRelation.MEETS,
    IntervalRelation.MET_BY,
}

_ADJACENT_RELATIONS = {
    IntervalRelation.MEETS,
    IntervalRelation.MET_BY,
}


def interval_relation(first: Span, second: Span) -> IntervalRelation:
    """Classify two non-empty right-open spans by Allen interval relation."""
    a0, a1 = first.start, first.end
    b0, b1 = second.start, second.end

    if a1 < b0:
        return IntervalRelation.BEFORE
    if a1 == b0:
        return IntervalRelation.MEETS
    if b1 < a0:
        return IntervalRelation.AFTER
    if b1 == a0:
        return IntervalRelation.MET_BY

    if a0 == b0:
        if a1 == b1:
            return IntervalRelation.EQUALS
        if a1 < b1:
            return IntervalRelation.STARTS
        return IntervalRelation.STARTED_BY

    if a1 == b1:
        if b0 < a0:
            return IntervalRelation.FINISHES
        return IntervalRelation.FINISHED_BY

    if a0 < b0:
        if a1 < b1:
            return IntervalRelation.OVERLAPS
        return IntervalRelation.CONTAINS

    if b1 < a1:
        return IntervalRelation.OVERLAPPED_BY
    return IntervalRelation.DURING


def span_pair_cases() -> tuple[SpanPairCase, ...]:
    """Generate every feasible relation, label, and singleton-extent combination."""
    cases: list[SpanPairCase] = []
    for relation in IntervalRelation:
        for first_singleton, second_singleton in product((True, False), repeat=2):
            coordinates = _coordinates(
                relation,
                first_singleton=first_singleton,
                second_singleton=second_singleton,
            )
            if coordinates is None:
                continue

            first_start, first_end, second_start, second_end = coordinates
            for same_label in (True, False):
                second_label = "X" if same_label else "Y"
                spans = (
                    Span(first_start, first_end, "X"),
                    Span(second_start, second_end, second_label),
                )
                cases.append(
                    SpanPairCase(
                        relation=relation,
                        same_label=same_label,
                        first_singleton=first_singleton,
                        second_singleton=second_singleton,
                        spans=spans,
                        length=max(first_end, second_end),
                    )
                )
    return tuple(cases)


def reference_span_pair_issue(
    case: SpanPairCase, *, scheme: str
) -> SpanPairIssue | None:
    """Classify pair representability from independent flat-family rules."""
    if case.relation is IntervalRelation.EQUALS and case.same_label:
        return SpanPairIssue.DUPLICATE
    if case.relation not in _FLAT_GEOMETRIC_RELATIONS:
        return SpanPairIssue.OVERLAP
    if case.relation in _ADJACENT_RELATIONS and case.same_label and scheme == "io":
        return SpanPairIssue.ADJACENT_SAME_LABEL
    return None


def _coordinates(
    relation: IntervalRelation,
    *,
    first_singleton: bool,
    second_singleton: bool,
) -> tuple[int, int, int, int] | None:
    direct = _FORWARD_GEOMETRY.get((relation, first_singleton, second_singleton))
    if direct is not None:
        return direct

    source_relation = _INVERSE_SOURCE.get(relation)
    if source_relation is None:
        return None

    source = _FORWARD_GEOMETRY.get((source_relation, second_singleton, first_singleton))
    if source is None:
        return None

    first_start, first_end, second_start, second_end = source
    return second_start, second_end, first_start, first_end
