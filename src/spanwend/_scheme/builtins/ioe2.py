"""Private strict IOE2 scheme declaration."""

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, FlatSchemeSpec
from spanwend._scheme.model import Scheme

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        body="I",
        end=Boundary("E"),
    ),
    display_name="IOE2",
)

IOE2 = Scheme(name="ioe2", aliases=(), codec=_CODEC)
