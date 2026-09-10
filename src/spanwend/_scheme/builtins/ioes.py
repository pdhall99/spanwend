"""Private IOES scheme declaration."""

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, FlatSchemeSpec
from spanwend._scheme.model import Scheme

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        body="I",
        end=Boundary("E"),
        singleton="S",
    ),
    display_name="IOES",
)

IOES = Scheme(name="ioes", aliases=(), codec=_CODEC)
