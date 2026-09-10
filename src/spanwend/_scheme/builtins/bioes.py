"""Private BIOES/IOBES scheme declaration."""

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, FlatSchemeSpec
from spanwend._scheme.model import Scheme

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        start=Boundary("B"),
        body="I",
        end=Boundary("E"),
        singleton="S",
    ),
    display_name="BIOES/IOBES",
)

BIOES = Scheme(name="bioes", aliases=("iobes",), codec=_CODEC)
