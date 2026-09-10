"""Tests for the generic scheme runtime boundary."""

from dataclasses import replace
from typing import cast

import pytest

from spanwend import (
    Diagnostic,
    DiagnosticCode,
    InvalidTagSequenceError,
    RepairPolicy,
    RepresentabilityResult,
    Span,
    check_conformance,
    check_representability,
    decode,
    encode,
)
from spanwend._input import _NormalizedSpans, _TagSequence
from spanwend._scheme.analysis import _Analysis
from spanwend._scheme.builtins.bio import BIO
from spanwend._scheme.builtins.registry import _SCHEMES, _SchemeKey
from spanwend._scheme.model import RepairRule, Scheme
from spanwend._scheme.runtime import repair as repair_scheme
from spanwend._syntax import DEFAULT_SYNTAX, TagSyntax

_OVERLAPPING = (
    Span(0, 2, "A"),
    Span(1, 3, "B"),
)
_TAGS = ("PAIR-A", "PAIR-B", "PAIR-END")


class _OverlappingCodec:
    """Synthetic non-flat codec whose canonical language permits overlap."""

    def analyze(
        self,
        tags: _TagSequence,
        *,
        syntax: TagSyntax = DEFAULT_SYNTAX,
    ) -> _Analysis:
        del syntax
        materialized = tuple(tags)
        if materialized == _TAGS:
            return _Analysis(_OVERLAPPING, ())
        return _Analysis((), ())

    def encode(
        self,
        spans: _NormalizedSpans,
        *,
        length: int,
        syntax: TagSyntax = DEFAULT_SYNTAX,
    ) -> tuple[str, ...]:
        del syntax
        assert tuple(spans) == _OVERLAPPING
        assert length == 3
        return tuple(_TAGS)

    def check_representability(
        self,
        spans: _NormalizedSpans,
        *,
        length: int,
    ) -> RepresentabilityResult:
        del spans, length
        return RepresentabilityResult()


@pytest.fixture
def non_flat_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    scheme = Scheme(
        name="synthetic-overlap",
        aliases=(),
        codec=_OverlappingCodec(),
    )
    monkeypatch.setitem(
        _SCHEMES,
        cast(_SchemeKey, "synthetic-overlap"),
        scheme,
    )


def test_public_runtime_does_not_impose_flat_span_constraints(
    non_flat_scheme: None,
) -> None:
    del non_flat_scheme
    scheme = cast(_SchemeKey, "synthetic-overlap")

    assert check_representability(_OVERLAPPING, length=3, scheme=scheme).representable
    tags = encode(_OVERLAPPING, length=3, scheme=scheme)
    assert tags == _TAGS
    assert check_conformance(tags, scheme=scheme).conformant
    assert decode(tags, scheme=scheme) == _OVERLAPPING


def test_repair_runtime_rejects_input_before_calling_transformation() -> None:
    def unexpected_repair(
        tags: tuple[str, ...], *, syntax: TagSyntax
    ) -> tuple[tuple[str, ...], tuple[Diagnostic, ...]]:
        pytest.fail("A repair callback must not receive input outside its domain")

    scheme = replace(
        BIO,
        repairs=(
            RepairRule(
                RepairPolicy.CONLLEVAL,
                unexpected_repair,
                repairable_codes=frozenset({DiagnosticCode.INVALID_START}),
            ),
        ),
    )
    tags = ("I-A", "BAD")

    with pytest.raises(InvalidTagSequenceError) as exc_info:
        repair_scheme(scheme, tags, policy=RepairPolicy.CONLLEVAL)

    assert (
        exc_info.value.diagnostics
        == check_conformance(
            tags,
            scheme="bio",
        ).diagnostics
    )


@pytest.mark.parametrize("output", [("I-A",), ("BAD",)])
def test_repair_runtime_rejects_invalid_transformation_output(
    output: tuple[str, ...],
) -> None:
    def invalid_repair(
        tags: tuple[str, ...], *, syntax: TagSyntax
    ) -> tuple[tuple[str, ...], tuple[Diagnostic, ...]]:
        return tuple(output), ()

    scheme = replace(
        BIO,
        repairs=(
            RepairRule(
                RepairPolicy.CONLLEVAL,
                invalid_repair,
                repairable_codes=frozenset(),
            ),
        ),
    )

    with pytest.raises(RuntimeError, match="produced a non-conformant 'bio' sequence"):
        repair_scheme(scheme, ("B-A",), policy=RepairPolicy.CONLLEVAL)


@pytest.mark.parametrize("changed", [False, True])
def test_repair_runtime_computes_changed(changed: bool) -> None:
    syntax = TagSyntax(separator=":", placement="suffix")
    raw_tags = ("A:I",) if changed else ("A:B",)
    repaired = ["A:B"]
    diagnostics = list(
        check_conformance(raw_tags, scheme="bio", syntax=syntax).diagnostics
    )
    expected_diagnostics = tuple(diagnostics)

    def rewrite(
        tags: tuple[str, ...], *, syntax: TagSyntax
    ) -> tuple[tuple[str, ...], tuple[Diagnostic, ...]]:
        assert tags == raw_tags
        assert syntax == TagSyntax(separator=":", placement="suffix")
        return tuple(repaired), tuple(diagnostics)

    scheme = replace(
        BIO,
        repairs=(
            RepairRule(
                RepairPolicy.CONLLEVAL,
                rewrite,
                repairable_codes=frozenset({DiagnosticCode.INVALID_START}),
            ),
        ),
    )

    result = repair_scheme(
        scheme, raw_tags, policy=RepairPolicy.CONLLEVAL, syntax=syntax
    )
    repaired.clear()
    diagnostics.clear()

    assert result.tags == ("A:B",)
    assert result.diagnostics == expected_diagnostics
    assert result.changed is changed
