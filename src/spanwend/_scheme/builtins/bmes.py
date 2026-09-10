"""Private BMES scheme declaration."""

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, FlatSchemeSpec
from spanwend._scheme.model import Scheme

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        start=Boundary("B"),
        body="M",
        end=Boundary("E"),
        singleton="S",
    ),
    display_name="BMES",
)

BMES = Scheme(name="bmes", aliases=(), codec=_CODEC)
