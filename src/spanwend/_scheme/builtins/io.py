"""Private IO scheme declaration."""

from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import FlatSchemeSpec
from spanwend._scheme.model import Scheme

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        body="I",
    ),
    display_name="IO",
)

IO = Scheme(name="io", aliases=(), codec=_CODEC)
