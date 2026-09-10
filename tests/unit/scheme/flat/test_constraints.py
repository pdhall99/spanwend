"""Parity proof for private flat transition constraints."""

from itertools import product

import pytest

from spanwend._scheme.builtins.registry import _BUILTIN_SCHEMES
from spanwend._scheme.flat.codec import FlatSpanCodec
from spanwend._scheme.flat.constraints import _compile_flat_constraints, _FlatLabelMode
from spanwend._scheme.flat.semantics import _FlatSemantics
from spanwend._scheme.flat.spec import FlatSchemeSpec
from spanwend._scheme.model import Scheme
from spanwend._scheme.runtime import check_conformance as _check_conformance
from spanwend._syntax import DEFAULT_SYNTAX, _ParsedTag

_LABELS = ("A", "B")
_MAX_SEQUENCE_LENGTH = 4


def _flat_codec(scheme: Scheme) -> FlatSpanCodec:
    assert isinstance(scheme.codec, FlatSpanCodec)
    return scheme.codec


def _alphabet(
    codec: FlatSpanCodec,
    label_mode: _FlatLabelMode,
) -> tuple[_ParsedTag, ...]:
    tags = [_ParsedTag("O", None)]
    for marker in sorted(codec.semantics.markers):
        if label_mode is _FlatLabelMode.LABELLED:
            tags.extend(_ParsedTag(marker, label) for label in _LABELS)
        else:
            tags.append(_ParsedTag(marker, None))
    return tuple(tags)


def _format(sequence: tuple[_ParsedTag, ...]) -> tuple[str, ...]:
    return tuple(DEFAULT_SYNTAX._format(tag) for tag in sequence)


@pytest.mark.parametrize("scheme", _BUILTIN_SCHEMES, ids=lambda scheme: scheme.name)
@pytest.mark.parametrize(
    "label_mode",
    tuple(_FlatLabelMode),
    ids=lambda mode: mode.name.lower(),
)
def test_constraints_match_strict_validation_exhaustively(
    scheme: Scheme,
    label_mode: _FlatLabelMode,
) -> None:
    codec = _flat_codec(scheme)
    constraints = _compile_flat_constraints(
        codec.semantics,
        label_mode=label_mode,
    )
    alphabet = _alphabet(codec, label_mode)

    for length in range(_MAX_SEQUENCE_LENGTH + 1):
        for sequence in product(alphabet, repeat=length):
            expected = _check_conformance(scheme, _format(sequence)).conformant
            actual = constraints.accepts(sequence)
            assert actual is expected, (
                f"scheme={scheme.name!r}, mode={label_mode.name.lower()!r}, "
                f"tags={_format(sequence)!r}"
            )


def test_label_mode_is_an_explicit_constraint_dimension() -> None:
    scheme = next(scheme for scheme in _BUILTIN_SCHEMES if scheme.name == "bio")
    semantics = _flat_codec(scheme).semantics
    sequence = (
        _ParsedTag("B", "PER"),
        _ParsedTag("O", None),
        _ParsedTag("B", None),
    )

    labelled = _compile_flat_constraints(
        semantics,
        label_mode=_FlatLabelMode.LABELLED,
    )
    unlabelled = _compile_flat_constraints(
        semantics,
        label_mode=_FlatLabelMode.UNLABELLED,
    )

    assert not labelled.accepts(sequence)
    assert not unlabelled.accepts(sequence)
    assert not _check_conformance(scheme, ("B-PER", "O", "B")).conformant


def test_contextual_boundaries_reduce_to_pairwise_conditions() -> None:
    iob1 = next(scheme for scheme in _BUILTIN_SCHEMES if scheme.name == "iob1")
    iob1_constraints = _compile_flat_constraints(
        _flat_codec(iob1).semantics,
        label_mode=_FlatLabelMode.LABELLED,
    )

    assert not iob1_constraints.allowed_start(_ParsedTag("B", "A"))
    assert iob1_constraints.allowed_transition(
        _ParsedTag("I", "A"),
        _ParsedTag("B", "A"),
    )
    assert not iob1_constraints.allowed_transition(
        _ParsedTag("I", "A"),
        _ParsedTag("B", "B"),
    )

    ioe1 = next(scheme for scheme in _BUILTIN_SCHEMES if scheme.name == "ioe1")
    ioe1_constraints = _compile_flat_constraints(
        _flat_codec(ioe1).semantics,
        label_mode=_FlatLabelMode.LABELLED,
    )

    assert not ioe1_constraints.allowed_end(_ParsedTag("E", "A"))
    assert ioe1_constraints.allowed_transition(
        _ParsedTag("E", "A"),
        _ParsedTag("I", "A"),
    )
    assert not ioe1_constraints.allowed_transition(
        _ParsedTag("E", "A"),
        _ParsedTag("I", "B"),
    )


def test_compiler_rejects_unproven_non_local_singleton_shape() -> None:
    semantics = _FlatSemantics(FlatSchemeSpec(body="I", singleton="S"))

    with pytest.raises(ValueError, match="first-order validity"):
        _compile_flat_constraints(
            semantics,
            label_mode=_FlatLabelMode.LABELLED,
        )
