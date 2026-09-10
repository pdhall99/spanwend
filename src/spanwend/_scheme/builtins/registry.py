"""Built-in scheme aggregation and case-insensitive lookup metadata."""

from typing import Literal, TypeAlias, cast, get_args

from spanwend._scheme.builtins.bilou import BILOU
from spanwend._scheme.builtins.bio import BIO
from spanwend._scheme.builtins.bioe import BIOE
from spanwend._scheme.builtins.bioes import BIOES
from spanwend._scheme.builtins.bios import BIOS
from spanwend._scheme.builtins.bmeow import BMEOW
from spanwend._scheme.builtins.bmes import BMES
from spanwend._scheme.builtins.io import IO
from spanwend._scheme.builtins.iob1 import IOB1
from spanwend._scheme.builtins.ioe1 import IOE1
from spanwend._scheme.builtins.ioe2 import IOE2
from spanwend._scheme.builtins.ioes import IOES
from spanwend._scheme.model import Scheme

_SchemeKey: TypeAlias = Literal[
    "io",
    "iob1",
    "bio",
    "iob2",
    "ioe1",
    "ioe2",
    "bios",
    "bioe",
    "bieo",
    "ioes",
    "bioes",
    "iobes",
    "bilou",
    "bioul",
    "bmes",
    "bmeow",
    "bmewo",
]

_BUILTIN_SCHEMES: tuple[Scheme, ...] = (
    IO,
    IOB1,
    BIO,
    IOE1,
    IOE2,
    BIOS,
    BIOE,
    IOES,
    BIOES,
    BILOU,
    BMES,
    BMEOW,
)


def _build_registry(schemes: tuple[Scheme, ...]) -> dict[_SchemeKey, Scheme]:
    """Build lookup keys from local scheme declarations and reject collisions."""
    registry: dict[_SchemeKey, Scheme] = {}
    for scheme in schemes:
        for raw_name in (scheme.name, *scheme.aliases):
            normalized = raw_name.casefold()
            name = cast(_SchemeKey, normalized)
            if name in registry:
                raise RuntimeError(
                    f"Duplicate built-in scheme name or alias {raw_name!r}"
                )
            registry[name] = scheme

    typed_names = set(get_args(_SchemeKey))
    registered_names = set(registry)
    if typed_names != registered_names:
        missing = sorted(registered_names - typed_names)
        stale = sorted(typed_names - registered_names)
        raise RuntimeError(
            "_SchemeKey and declared built-in names differ; "
            f"missing from _SchemeKey={missing!r}, stale in _SchemeKey={stale!r}"
        )

    return registry


_SCHEMES = _build_registry(_BUILTIN_SCHEMES)
