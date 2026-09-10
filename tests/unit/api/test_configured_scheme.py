"""Tests for the configured public scheme façade."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from spanwend import (
    ConfiguredScheme,
    DiagnosticCode,
    RepresentabilityCode,
    Span,
    TagSyntax,
    scheme,
)


def test_scheme_factory_canonicalizes_aliases() -> None:
    bio = scheme("bio")
    alias = scheme("iob2")

    assert alias.name == "bio"
    assert alias == bio
    assert hash(alias) == hash(bio)


def test_configured_scheme_accepts_existing_tag_syntax() -> None:
    syntax = TagSyntax(separator=":", placement="suffix", outside="_")

    direct = ConfiguredScheme("bio", syntax=syntax)
    configured = scheme("bio", separator=":", placement="suffix", outside="_")

    assert direct == configured
    assert configured.syntax == syntax


def test_configured_scheme_rejects_non_tag_syntax() -> None:
    invalid_syntax = cast(TagSyntax, object())

    with pytest.raises(TypeError, match="ConfiguredScheme.syntax: expected TagSyntax"):
        ConfiguredScheme("bio", syntax=invalid_syntax)


def test_configured_scheme_is_immutable() -> None:
    bio = scheme("bio")

    with pytest.raises(FrozenInstanceError):
        setattr(bio, "name", "io")


def test_configured_scheme_delegates_core_operations() -> None:
    bio = scheme("bio")
    spans = [(0, 2, "PER"), (3, 4, "ORG")]
    tags = ("B-PER", "I-PER", "O", "B-ORG")

    assert bio.decode(tags) == (
        Span(0, 2, "PER"),
        Span(3, 4, "ORG"),
    )
    assert bio.encode(spans, length=4) == tags
    assert bio.check_representability(spans, length=4).representable

    conformance = bio.check_conformance(("I-PER", "I-PER"))
    assert not conformance.conformant
    assert conformance.diagnostics[0].code is DiagnosticCode.INVALID_START

    repaired = bio.repair(("O", "I-PER", "I-PER"), policy="conlleval")
    assert repaired.tags == ("O", "B-PER", "I-PER")
    assert repaired.changed


def test_configured_scheme_uses_bound_syntax() -> None:
    bio = scheme("bio", separator=":", placement="suffix", outside="_")
    spans = [(0, 2, "PER")]

    tags = bio.encode(spans, length=3)

    assert tags == ("PER:B", "PER:I", "_")
    assert bio.decode(tags) == (Span(0, 2, "PER"),)


def test_convert_to_string_target_uses_default_target_syntax() -> None:
    source = scheme("bio", separator=":", placement="suffix", outside="_")
    tags = ("PER:B", "_", "ORG:B", "ORG:I")

    assert source.convert(tags, target="bilou") == (
        "U-PER",
        "O",
        "B-ORG",
        "L-ORG",
    )


def test_convert_to_configured_target_uses_target_syntax() -> None:
    source = scheme("bio", separator=":", placement="suffix", outside="_")
    target = scheme("bilou", separator=":", outside="NONE")
    tags = ("PER:B", "_", "ORG:B", "ORG:I")

    assert source.convert(tags, target=target) == (
        "U:PER",
        "NONE",
        "B:ORG",
        "L:ORG",
    )


def test_representability_is_independent_of_bound_syntax() -> None:
    io = scheme("io", separator=":", placement="suffix", outside="_")
    adjacent_same_label = [(0, 1, "PER"), (1, 2, "PER")]

    result = io.check_representability(adjacent_same_label, length=2)

    assert not result.representable
    assert result.code is RepresentabilityCode.ADJACENT_SAME_LABEL
