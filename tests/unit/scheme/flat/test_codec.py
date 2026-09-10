"""Conformance tests for built-ins built from flat scheme declarations."""

import pytest

from spanwend import DiagnosticCode, Span, TagSyntax
from spanwend._input import _normalize_spans
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
from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, FlatSchemeSpec
from spanwend._scheme.model import SchemeCodec
from tests.conformance._conformance import (
    SYNTAXES,
    format_tag,
    reference_decode,
    reference_encode,
    reference_is_representable,
    reference_is_valid,
    span_collections,
    tag_sequences,
)

_CODECS: dict[str, SchemeCodec] = {
    "io": IO.codec,
    "iob1": IOB1.codec,
    "bio": BIO.codec,
    "bioe": BIOE.codec,
    "bios": BIOS.codec,
    "ioe1": IOE1.codec,
    "ioe2": IOE2.codec,
    "ioes": IOES.codec,
    "bioes": BIOES.codec,
    "bilou": BILOU.codec,
    "bmes": BMES.codec,
    "bmeow": BMEOW.codec,
}


@pytest.mark.parametrize("scheme", tuple(_CODECS))
@pytest.mark.parametrize("syntax", SYNTAXES)
def test_flat_codec_matches_independent_validity_and_decode(
    scheme: str,
    syntax: TagSyntax,
) -> None:
    codec = _CODECS[scheme]

    for semantic_tags in tag_sequences(scheme, max_length=3):
        tags = tuple(format_tag(tag, syntax) for tag in semantic_tags)
        analysis = codec.analyze(tags, syntax=syntax)
        expected_valid = reference_is_valid(semantic_tags, scheme)

        assert (not analysis.diagnostics) is expected_valid
        if expected_valid:
            assert analysis.spans == reference_decode(semantic_tags, scheme)


@pytest.mark.parametrize("scheme", tuple(_CODECS))
@pytest.mark.parametrize("syntax", SYNTAXES)
def test_flat_codec_matches_independent_encoding_and_representability(
    scheme: str,
    syntax: TagSyntax,
) -> None:
    codec = _CODECS[scheme]

    for length in range(4):
        for spans in span_collections(length):
            normalized = _normalize_spans(spans)
            expected_representable = reference_is_representable(
                normalized,
                length=length,
                scheme=scheme,
            )
            result = codec.check_representability(normalized, length=length)

            assert result.representable is expected_representable
            if expected_representable:
                assert codec.encode(normalized, length=length, syntax=syntax) == (
                    reference_encode(
                        normalized,
                        length=length,
                        scheme=scheme,
                        syntax=syntax,
                    )
                )


@pytest.mark.parametrize(
    ("scheme", "tags", "codes"),
    [
        ("bio", ("I-PER",), [DiagnosticCode.INVALID_START]),
        (
            "bio",
            ("B-PER", "I-ORG"),
            [DiagnosticCode.LABEL_MISMATCH],
        ),
        ("bioe", ("I-PER",), [DiagnosticCode.INVALID_START]),
        (
            "bioe",
            ("B-PER", "I-ORG"),
            [DiagnosticCode.LABEL_MISMATCH],
        ),
        ("iob1", ("B-PER",), [DiagnosticCode.INVALID_BOUNDARY]),
        ("ioe1", ("E-PER",), [DiagnosticCode.INVALID_BOUNDARY]),
        ("ioe2", ("I-PER",), [DiagnosticCode.UNTERMINATED_SPAN]),
        (
            "ioe2",
            ("I-PER", "O"),
            [DiagnosticCode.INVALID_TRANSITION],
        ),
        ("bioes", ("I-PER",), [DiagnosticCode.INVALID_START]),
        ("bilou", ("L-PER",), [DiagnosticCode.INVALID_START]),
        ("bmes", ("M-PER",), [DiagnosticCode.INVALID_START]),
        ("bmeow", ("M-PER",), [DiagnosticCode.INVALID_START]),
    ],
)
def test_flat_codec_preserves_structured_diagnostic_kinds(
    scheme: str,
    tags: tuple[str, ...],
    codes: list[DiagnosticCode],
) -> None:
    analysis = _CODECS[scheme].analyze(tags)

    assert [diagnostic.code for diagnostic in analysis.diagnostics] == codes


def test_flat_codec_preserves_actionable_boundary_guidance() -> None:
    assert "scheme='iob1'" in (
        _CODECS["bio"].analyze(("I-PER",)).diagnostics[0].message
    )
    assert "scheme='bio'/'iob2'" in (
        _CODECS["iob1"].analyze(("B-PER",)).diagnostics[0].message
    )
    assert "scheme='ioe2'" in (
        _CODECS["ioe1"].analyze(("E-PER",)).diagnostics[0].message
    )


def test_io_derives_adjacent_same_label_loss_from_boundary_semantics() -> None:
    spans = _normalize_spans([Span(0, 1, "PER"), Span(1, 2, "PER")])

    result = IO.codec.check_representability(spans, length=2)

    assert not result.representable
    assert result.message is not None
    assert "adjacent spans with the same label" in result.message


def test_explicit_flat_codec_accepts_non_b_start_marker() -> None:
    codec = build_flat_codec(
        FlatSchemeSpec(
            start=Boundary("A"),
            body="I",
            end=Boundary("E"),
            singleton="S",
        ),
        display_name="synthetic explicit",
    )
    spans = _normalize_spans([Span(0, 2, "X"), Span(2, 3, "Y")])

    tags = codec.encode(spans, length=3)
    analysis = codec.analyze(tags)

    assert tags == ("A-X", "E-X", "S-Y")
    assert analysis.diagnostics == ()
    assert analysis.spans == spans


@pytest.mark.parametrize(
    ("name", "spec", "spans", "expected"),
    [
        (
            "BIOE-like",
            FlatSchemeSpec(
                body="I",
                start=Boundary("B"),
                end=Boundary("E"),
                singleton="B",
            ),
            (Span(0, 1, "X"), Span(1, 4, "X")),
            ("B-X", "B-X", "I-X", "E-X"),
        ),
        (
            "BIOS-like",
            FlatSchemeSpec(
                body="I",
                start=Boundary("B"),
                singleton="S",
            ),
            (Span(0, 1, "X"), Span(1, 3, "X")),
            ("S-X", "B-X", "I-X"),
        ),
        (
            "IOES-like",
            FlatSchemeSpec(
                body="I",
                end=Boundary("E"),
                singleton="S",
            ),
            (Span(0, 2, "X"), Span(2, 3, "X")),
            ("I-X", "E-X", "S-X"),
        ),
    ],
)
def test_flat_boundary_semantics_support_design_cells_without_branches(
    name: str,
    spec: FlatSchemeSpec,
    spans: tuple[Span, ...],
    expected: tuple[str, ...],
) -> None:
    codec = build_flat_codec(spec, display_name=name)
    normalized = _normalize_spans(spans)

    assert codec.encode(normalized, length=len(expected)) == expected
    analysis = codec.analyze(expected)

    assert analysis.diagnostics == ()
    assert analysis.spans == normalized


@pytest.mark.parametrize(
    ("spec", "tags", "code"),
    [
        (
            FlatSchemeSpec(
                body="I",
                start=Boundary("B"),
                singleton="S",
            ),
            ("B-X",),
            DiagnosticCode.UNTERMINATED_SPAN,
        ),
        (
            FlatSchemeSpec(
                body="I",
                end=Boundary("E"),
                singleton="S",
            ),
            ("E-X",),
            DiagnosticCode.INVALID_START,
        ),
    ],
)
def test_singleton_override_excludes_ordinary_singleton_spelling(
    spec: FlatSchemeSpec,
    tags: tuple[str, ...],
    code: DiagnosticCode,
) -> None:
    codec = build_flat_codec(spec, display_name="synthetic")

    assert [item.code for item in codec.analyze(tags).diagnostics] == [code]


@pytest.mark.parametrize(
    ("tags", "code"),
    [
        (("I-X",), DiagnosticCode.INVALID_START),
        (("B-X", "I-Y"), DiagnosticCode.LABEL_MISMATCH),
        (("B-X", "B-Y"), DiagnosticCode.INVALID_TRANSITION),
    ],
)
def test_bios_like_recovery_does_not_cascade_diagnostics(
    tags: tuple[str, ...],
    code: DiagnosticCode,
) -> None:
    codec = build_flat_codec(
        FlatSchemeSpec(
            body="I",
            start=Boundary("B"),
            singleton="S",
        ),
        display_name="synthetic BIOS",
    )

    assert [item.code for item in codec.analyze(tags).diagnostics] == [code]


def test_singleton_only_vocabulary_preserves_some_same_label_adjacencies() -> None:
    codec = build_flat_codec(
        FlatSchemeSpec(body="I", singleton="S"),
        display_name="synthetic IOS",
    )
    with_singleton = _normalize_spans([Span(0, 1, "X"), Span(1, 3, "X")])
    both_multi = _normalize_spans([Span(0, 2, "X"), Span(2, 4, "X")])

    assert codec.check_representability(with_singleton, length=3).representable
    assert not codec.check_representability(both_multi, length=4).representable

    tags = codec.encode(with_singleton, length=3)
    assert tags == ("S-X", "I-X", "I-X")
    assert codec.analyze(tags).spans == with_singleton
