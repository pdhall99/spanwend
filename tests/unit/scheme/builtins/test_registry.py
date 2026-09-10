"""Tests for built-in scheme registration and public name resolution."""

from typing import cast, get_args

import pytest

from spanwend import check_conformance
from spanwend._scheme.builtins.io import IO
from spanwend._scheme.builtins.registry import (
    _BUILTIN_SCHEMES,
    _SCHEMES,
    _build_registry,
    _SchemeKey,
)
from spanwend._scheme.model import Scheme


def test_registry_keys_match_declared_names_and_public_type() -> None:
    declared = {
        name for scheme in _BUILTIN_SCHEMES for name in (scheme.name, *scheme.aliases)
    }

    assert set(_SCHEMES) == declared
    assert set(get_args(_SchemeKey)) == declared


def test_registry_values_are_the_declared_schemes() -> None:
    for scheme in _BUILTIN_SCHEMES:
        assert _SCHEMES[cast(_SchemeKey, scheme.name)] is scheme
        for alias in scheme.aliases:
            assert _SCHEMES[cast(_SchemeKey, alias)] is scheme


def test_registry_rejects_case_insensitive_cross_scheme_collision() -> None:
    first = Scheme(name="synthetic", aliases=(), codec=IO.codec)
    second = Scheme(name="SYNTHETIC", aliases=(), codec=IO.codec)

    with pytest.raises(RuntimeError, match="Duplicate built-in scheme"):
        _build_registry((first, second))


@pytest.mark.parametrize(
    "name",
    [
        "io",
        "IOB1",
        "bio",
        "IOB2",
        "BIOE",
        "BIEO",
        "BIOS",
        "ioe1",
        "IOE2",
        "IOES",
        "BIOES",
        "iobes",
        "bilou",
        "BIOUL",
        "bmes",
        "BMEOW",
        "bmewo",
    ],
)
def test_scheme_names_and_aliases_are_case_insensitive(name: str) -> None:
    assert check_conformance(["O"], scheme=name).conformant  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("iob2", "bio"),
        ("bieo", "bioe"),
        ("iobes", "bioes"),
        ("bioul", "bilou"),
        ("bmewo", "bmeow"),
    ],
)
def test_scheme_aliases_share_canonical_semantics(
    alias: _SchemeKey,
    canonical: _SchemeKey,
) -> None:
    assert check_conformance(["O"], scheme=alias) == check_conformance(
        ["O"],
        scheme=canonical,
    )


def test_bare_iob_is_rejected_as_ambiguous() -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        check_conformance(["O"], scheme="iob")  # type: ignore[arg-type]


def test_unknown_scheme_is_rejected() -> None:
    with pytest.raises(ValueError, match="scheme: expected one of"):
        check_conformance(["O"], scheme="unknown")  # type: ignore[arg-type]


def test_non_string_scheme_is_rejected() -> None:
    with pytest.raises(TypeError, match="scheme: expected str, got int"):
        check_conformance(["O"], scheme=3)  # type: ignore[arg-type]
