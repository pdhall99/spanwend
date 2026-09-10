"""Tests for the private scheme metadata and codec boundary."""

import pytest

from spanwend._diagnostic import Diagnostic
from spanwend._input import _NormalizedSpans, _TagSequence
from spanwend._repair import RepairPolicy
from spanwend._representability import RepresentabilityResult
from spanwend._scheme.analysis import _Analysis
from spanwend._scheme.model import RepairRule, Scheme, SchemeCodec
from spanwend._syntax import DEFAULT_SYNTAX, TagSyntax


class _NonFlatCodec:
    def analyze(
        self,
        tags: _TagSequence,
        *,
        syntax: TagSyntax = DEFAULT_SYNTAX,
    ) -> _Analysis:
        del tags, syntax
        return _Analysis((), ())

    def encode(
        self,
        spans: _NormalizedSpans,
        *,
        length: int,
        syntax: TagSyntax = DEFAULT_SYNTAX,
    ) -> tuple[str, ...]:
        del spans
        return (syntax.outside,) * length

    def check_representability(
        self,
        spans: _NormalizedSpans,
        *,
        length: int,
    ) -> RepresentabilityResult:
        del spans, length
        return RepresentabilityResult()


def _repair(
    tags: _TagSequence,
    *,
    syntax: TagSyntax = DEFAULT_SYNTAX,
) -> tuple[tuple[str, ...], tuple[Diagnostic, ...]]:
    del syntax
    return tuple(tags), ()


def _require_codec(codec: SchemeCodec) -> SchemeCodec:
    return codec


def test_scheme_accepts_structural_non_flat_codec_and_repair_rules() -> None:
    codec = _NonFlatCodec()
    rule = RepairRule(RepairPolicy.CONLLEVAL, _repair, repairable_codes=frozenset())

    scheme = Scheme(
        name="synthetic",
        aliases=("syn",),
        codec=_require_codec(codec),
        repairs=(rule,),
    )

    assert scheme.codec is codec
    assert scheme.aliases == ("syn",)
    assert scheme.repair_rule_for(RepairPolicy.CONLLEVAL) is rule
    assert scheme.repair_rule_for(RepairPolicy.DISCARD) is None


def test_scheme_rejects_case_insensitive_name_alias_collision() -> None:
    with pytest.raises(ValueError, match="unique ignoring case"):
        Scheme(
            name="bio",
            aliases=("BIO",),
            codec=_require_codec(_NonFlatCodec()),
        )


def test_scheme_rejects_duplicate_repair_policy() -> None:
    with pytest.raises(ValueError, match="repair policies must be unique"):
        Scheme(
            name="synthetic",
            aliases=(),
            codec=_require_codec(_NonFlatCodec()),
            repairs=(
                RepairRule(RepairPolicy.CONLLEVAL, _repair, frozenset()),
                RepairRule(RepairPolicy.CONLLEVAL, _repair, frozenset()),
            ),
        )
