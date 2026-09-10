"""Private contextual IOE1 scheme declaration."""

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, BoundaryCondition, FlatSchemeSpec
from spanwend._scheme.model import Scheme

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        body="I",
        end=Boundary("E", BoundaryCondition.ADJACENT_SAME_LABEL),
    ),
    display_name="IOE1",
    invalid_boundary_guidance=("If every span ends with E, use scheme='ioe2' instead."),
)

IOE1 = Scheme(name="ioe1", aliases=(), codec=_CODEC)
