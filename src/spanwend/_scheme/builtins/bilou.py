"""Private BILOU/BIOUL scheme declaration."""

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, FlatSchemeSpec
from spanwend._scheme.model import Scheme

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        start=Boundary("B"),
        body="I",
        end=Boundary("L"),
        singleton="U",
    ),
    display_name="BILOU/BIOUL",
)

BILOU = Scheme(name="bilou", aliases=("bioul",), codec=_CODEC)
