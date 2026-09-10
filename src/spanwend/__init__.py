"""Loss-aware operations for sequence tags and labelled spans."""

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

__all__ = [
    "DEFAULT_SYNTAX",
    "ConfiguredScheme",
    "ConformanceResult",
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
    "check_conformance",
    "check_representability",
    "convert",
    "decode",
    "encode",
    "repair",
    "scheme",
]
