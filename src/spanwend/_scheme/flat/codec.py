"""Adapter joining flat scheme analysis, representability, and encoding."""

from dataclasses import dataclass

from spanwend._diagnostic import DiagnosticCode
from spanwend._error import UnrepresentableError
from spanwend._input import _NormalizedSpans, _TagSequence
from spanwend._representability import RepresentabilityResult
from spanwend._scheme.analysis import (
    _Analysis,
    _parse_sequence,
    _prepare_label_mode,
    _restore_unlabelled_spans,
)
from spanwend._scheme.flat.analysis import _FlatSpanAnalyzer
from spanwend._scheme.flat.encoding import _encode_flat
from spanwend._scheme.flat.representability import _check_flat_representability
from spanwend._scheme.flat.semantics import _FlatSemantics
from spanwend._scheme.flat.spec import FlatSchemeSpec, _require_supported_codec_spec
from spanwend._syntax import DEFAULT_SYNTAX, TagSyntax


@dataclass(frozen=True, slots=True)
class FlatSpanCodec:
    """Implement the scheme codec interface using flat boundary semantics."""

    semantics: _FlatSemantics
    display_name: str
    invalid_start_guidance: str = ""
    invalid_boundary_guidance: str = ""

    def analyze(
        self,
        tags: _TagSequence,
        *,
        syntax: TagSyntax = DEFAULT_SYNTAX,
    ) -> _Analysis:
        """Parse once, validate label mode, then run flat semantic analysis."""
        sequence, syntax_diagnostics = _parse_sequence(tags, syntax)
        (
            sequence,
            label_diagnostics,
            unlabelled_mode,
            mixed_indices,
        ) = _prepare_label_mode(sequence)
        analyzer = _FlatSpanAnalyzer(
            semantics=self.semantics,
            display_name=self.display_name,
            invalid_start_guidance=self.invalid_start_guidance,
            invalid_boundary_guidance=self.invalid_boundary_guidance,
        )
        scheme_result = analyzer.analyze_parsed(sequence)
        scheme_diagnostics = tuple(
            diagnostic
            for diagnostic in scheme_result.diagnostics
            if not (
                diagnostic.code is DiagnosticCode.LABEL_MISMATCH
                and diagnostic.index in mixed_indices
            )
        )
        diagnostics = tuple(
            sorted(
                (
                    *syntax_diagnostics,
                    *label_diagnostics,
                    *scheme_diagnostics,
                ),
                key=lambda diagnostic: (diagnostic.index, diagnostic.code.value),
            )
        )
        spans = _restore_unlabelled_spans(
            scheme_result.spans,
            unlabelled_mode=unlabelled_mode,
        )
        return _Analysis(spans, diagnostics)

    def check_representability(
        self,
        spans: _NormalizedSpans,
        *,
        length: int,
    ) -> RepresentabilityResult:
        """Check flat-layer loss constraints derived from boundary semantics."""
        return _check_flat_representability(
            spans,
            length=length,
            semantics=self.semantics,
        )

    def encode(
        self,
        spans: _NormalizedSpans,
        *,
        length: int,
        syntax: TagSyntax = DEFAULT_SYNTAX,
    ) -> tuple[str, ...]:
        """Check representability, then emit tags from boundary semantics."""
        result = self.check_representability(spans, length=length)
        if not result.representable:
            assert result.code is not None
            assert result.message is not None
            raise UnrepresentableError(result.code, result.message)

        return _encode_flat(
            self.semantics,
            spans,
            length=length,
            syntax=syntax,
        )


def build_flat_codec(
    spec: FlatSchemeSpec,
    *,
    display_name: str,
    invalid_start_guidance: str = "",
    invalid_boundary_guidance: str = "",
) -> FlatSpanCodec:
    """Validate one flat declaration and build its runtime codec."""
    _require_supported_codec_spec(
        spec,
        invalid_start_guidance=invalid_start_guidance,
        invalid_boundary_guidance=invalid_boundary_guidance,
    )
    return FlatSpanCodec(
        semantics=_FlatSemantics(spec),
        display_name=display_name,
        invalid_start_guidance=invalid_start_guidance,
        invalid_boundary_guidance=invalid_boundary_guidance,
    )
