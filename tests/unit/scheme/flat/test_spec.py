"""Tests for declarative flat contiguous-span scheme specifications."""

import pytest

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, BoundaryCondition, FlatSchemeSpec


def test_flat_scheme_spec_expresses_contextual_start_boundary() -> None:
    spec = FlatSchemeSpec(
        body="I",
        start=Boundary("B", BoundaryCondition.ADJACENT_SAME_LABEL),
    )

    assert spec.start == Boundary("B", BoundaryCondition.ADJACENT_SAME_LABEL)
    assert spec.body == "I"
    assert spec.end is None
    assert spec.singleton is None


def test_flat_scheme_spec_expresses_explicit_boundary_vocabulary() -> None:
    spec = FlatSchemeSpec(
        body="I",
        start=Boundary("B"),
        end=Boundary("L"),
        singleton="U",
    )

    assert spec == FlatSchemeSpec(
        body="I",
        start=Boundary("B", BoundaryCondition.ALWAYS),
        end=Boundary("L", BoundaryCondition.ALWAYS),
        singleton="U",
    )


def test_flat_scheme_spec_allows_singleton_to_reuse_start_marker() -> None:
    spec = FlatSchemeSpec(
        body="I",
        start=Boundary("B"),
        end=Boundary("E"),
        singleton="B",
    )

    assert spec.singleton == "B"


def test_flat_scheme_spec_allows_start_body_singleton_shape() -> None:
    spec = FlatSchemeSpec(
        body="I",
        start=Boundary("B"),
        singleton="S",
    )

    assert spec.start == Boundary("B")
    assert spec.end is None
    assert spec.singleton == "S"


def test_flat_scheme_spec_allows_body_end_singleton_shape() -> None:
    spec = FlatSchemeSpec(
        body="I",
        end=Boundary("E"),
        singleton="S",
    )

    assert spec.start is None
    assert spec.end == Boundary("E")
    assert spec.singleton == "S"


def test_flat_scheme_spec_rejects_duplicate_boundary_markers() -> None:
    with pytest.raises(ValueError, match="must be distinct"):
        FlatSchemeSpec(
            body="I",
            start=Boundary("I"),
        )


def test_flat_scheme_spec_rejects_singleton_body_collision() -> None:
    with pytest.raises(ValueError, match="singleton marker must differ"):
        FlatSchemeSpec(
            body="I",
            singleton="I",
        )


def test_flat_scheme_spec_requires_singleton_with_both_boundaries() -> None:
    with pytest.raises(ValueError, match="require a singleton override"):
        FlatSchemeSpec(
            body="I",
            start=Boundary("B"),
            end=Boundary("E"),
        )


def test_flat_scheme_spec_rejects_outside_marker() -> None:
    with pytest.raises(ValueError, match="reserved for outside"):
        FlatSchemeSpec(body="O")


def test_flat_codec_rejects_start_guidance_without_start_boundary() -> None:
    with pytest.raises(ValueError, match="Start guidance"):
        build_flat_codec(
            FlatSchemeSpec(body="I"),
            display_name="synthetic",
            invalid_start_guidance="Use another scheme.",
        )


def test_flat_codec_rejects_boundary_guidance_without_contextual_boundary() -> None:
    with pytest.raises(ValueError, match="Boundary guidance"):
        build_flat_codec(
            FlatSchemeSpec(body="I", start=Boundary("B")),
            display_name="synthetic",
            invalid_boundary_guidance="Use another scheme.",
        )
