"""Exhaustive two-span conformance tests from Allen interval relations."""

from collections import defaultdict

import pytest

from spanwend import (
    UnrepresentableError,
    check_representability,
    decode,
    encode,
)
from spanwend._scheme.builtins.registry import _SchemeKey
from tests.conformance._conformance import IMPLEMENTED_SCHEMES, normalize
from tests.conformance._intervals import (
    IntervalRelation,
    SpanPairCase,
    SpanPairIssue,
    interval_relation,
    reference_span_pair_issue,
    span_pair_cases,
)

_SPAN_PAIR_CASES = span_pair_cases()

_ALL_EXTENTS: set[tuple[bool, bool]] = {
    (True, True),
    (True, False),
    (False, True),
    (False, False),
}
_EXPECTED_EXTENTS: dict[IntervalRelation, set[tuple[bool, bool]]] = {
    IntervalRelation.BEFORE: _ALL_EXTENTS,
    IntervalRelation.AFTER: _ALL_EXTENTS,
    IntervalRelation.MEETS: _ALL_EXTENTS,
    IntervalRelation.MET_BY: _ALL_EXTENTS,
    IntervalRelation.OVERLAPS: {(False, False)},
    IntervalRelation.OVERLAPPED_BY: {(False, False)},
    IntervalRelation.STARTS: {(True, False), (False, False)},
    IntervalRelation.STARTED_BY: {(False, True), (False, False)},
    IntervalRelation.DURING: {(True, False), (False, False)},
    IntervalRelation.CONTAINS: {(False, True), (False, False)},
    IntervalRelation.FINISHES: {(True, False), (False, False)},
    IntervalRelation.FINISHED_BY: {(False, True), (False, False)},
    IntervalRelation.EQUALS: {(True, True), (False, False)},
}

_ERROR_FRAGMENT = {
    SpanPairIssue.DUPLICATE: "Duplicate span occurrence",
    SpanPairIssue.OVERLAP: "Overlapping spans",
    SpanPairIssue.ADJACENT_SAME_LABEL: "cannot distinguish adjacent spans",
}

_SPAN_PAIR_PARAMETERS = tuple(
    (scheme, case) for scheme in IMPLEMENTED_SCHEMES for case in _SPAN_PAIR_CASES
)
_SPAN_PAIR_IDS = tuple(
    f"{scheme}-{case.case_id}" for scheme, case in _SPAN_PAIR_PARAMETERS
)
_REPRESENTABLE_PARAMETERS = tuple(
    (scheme, case)
    for scheme, case in _SPAN_PAIR_PARAMETERS
    if reference_span_pair_issue(case, scheme=scheme) is None
)
_REPRESENTABLE_IDS = tuple(
    f"{scheme}-{case.case_id}" for scheme, case in _REPRESENTABLE_PARAMETERS
)


def test_span_pair_generator_covers_exact_feasible_extent_cells() -> None:
    generated: dict[IntervalRelation, set[tuple[bool, bool]]] = defaultdict(set)
    for case in _SPAN_PAIR_CASES:
        generated[case.relation].add((case.first_singleton, case.second_singleton))

    assert dict(generated) == _EXPECTED_EXTENTS
    assert sum(len(extents) for extents in generated.values()) == 32
    assert len(_SPAN_PAIR_CASES) == 64


def test_span_pair_generator_covers_both_label_relations_per_geometry() -> None:
    label_axes: dict[tuple[IntervalRelation, bool, bool], set[bool]] = defaultdict(set)
    for case in _SPAN_PAIR_CASES:
        key = (
            case.relation,
            case.first_singleton,
            case.second_singleton,
        )
        label_axes[key].add(case.same_label)

    assert all(values == {True, False} for values in label_axes.values())


@pytest.mark.parametrize(
    "case",
    _SPAN_PAIR_CASES,
    ids=lambda case: case.case_id,
)
def test_generated_span_pair_matches_declared_metadata(case: SpanPairCase) -> None:
    first, second = case.spans

    assert interval_relation(first, second) is case.relation
    assert (first.end - first.start == 1) is case.first_singleton
    assert (second.end - second.start == 1) is case.second_singleton
    assert (first.label == second.label) is case.same_label
    assert case.length == max(first.end, second.end)


@pytest.mark.parametrize(
    ("scheme", "case"),
    _SPAN_PAIR_PARAMETERS,
    ids=_SPAN_PAIR_IDS,
)
def test_span_pair_representability_matches_independent_allen_model(
    scheme: _SchemeKey,
    case: SpanPairCase,
) -> None:
    expected_issue = reference_span_pair_issue(case, scheme=scheme)
    expected = expected_issue is None

    assert (
        check_representability(
            case.spans,
            length=case.length,
            scheme=scheme,
        ).representable
        is expected
    )

    if expected_issue is None:
        return

    with pytest.raises(UnrepresentableError) as exc_info:
        encode(case.spans, length=case.length, scheme=scheme)
    assert _ERROR_FRAGMENT[expected_issue] in str(exc_info.value)


@pytest.mark.parametrize(
    ("scheme", "case"),
    _REPRESENTABLE_PARAMETERS,
    ids=_REPRESENTABLE_IDS,
)
def test_representable_span_pairs_encode_decode_round_trip(
    scheme: _SchemeKey,
    case: SpanPairCase,
) -> None:
    assert check_representability(
        case.spans,
        length=case.length,
        scheme=scheme,
    ).representable

    tags = encode(case.spans, length=case.length, scheme=scheme)

    assert decode(tags, scheme=scheme) == normalize(case.spans)
