"""Private BMEOW/BMEWO scheme declaration."""

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, FlatSchemeSpec
from spanwend._scheme.model import Scheme

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        start=Boundary("B"),
        body="M",
        end=Boundary("E"),
        singleton="W",
    ),
    display_name="BMEOW/BMEWO",
)

BMEOW = Scheme(name="bmeow", aliases=("bmewo",), codec=_CODEC)
