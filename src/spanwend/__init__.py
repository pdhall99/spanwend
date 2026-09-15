"""A library for working with sequence-tagging schemes."""

from importlib.metadata import PackageNotFoundError, version

from spanwend._api import (
    check_conformance,
    check_representability,
    convert,
    decode,
    encode,
    repair,
)
from spanwend._configured import ConfiguredScheme, scheme
from spanwend._conformance import ConformanceResult
from spanwend._diagnostic import Diagnostic, DiagnosticCode
from spanwend._error import InvalidTagSequenceError, SpanwendError, UnrepresentableError
from spanwend._input import SpanInput, SpanMapping, SpanTuple
from spanwend._repair import RepairPolicy, RepairResult
from spanwend._representability import RepresentabilityCode, RepresentabilityResult
from spanwend._span import Span
from spanwend._syntax import DEFAULT_SYNTAX, TagSyntax

try:
    __version__ = version("spanwend")
except PackageNotFoundError:
    __version__ = "unknown"
finally:
    del PackageNotFoundError, version

__all__ = [
    "ConfiguredScheme",
    "ConformanceResult",
    "DEFAULT_SYNTAX",
    "Diagnostic",
    "DiagnosticCode",
    "InvalidTagSequenceError",
    "RepairPolicy",
    "RepairResult",
    "RepresentabilityCode",
    "RepresentabilityResult",
    "Span",
    "SpanInput",
    "SpanMapping",
    "SpanTuple",
    "SpanwendError",
    "TagSyntax",
    "UnrepresentableError",
    "__version__",
    "check_conformance",
    "check_representability",
    "convert",
    "decode",
    "encode",
    "repair",
    "scheme",
]
