"""Tests for semantics specific to BIOES/IOBES and BILOU/BIOUL."""

import pytest

from spanwend import (
    DiagnosticCode,
    InvalidTagSequenceError,
    Span,
    check_conformance,
    decode,
    encode,
)
from spanwend._scheme.builtins.registry import _SchemeKey


@pytest.mark.parametrize(
    ("scheme", "single", "end"),
    [("bioes", "S", "E"), ("bilou", "U", "L")],
)
def test_explicit_boundary_encodes_span_lengths(
    scheme: _SchemeKey,
    single: str,
    end: str,
) -> None:
    spans = [Span(0, 1, "PER"), Span(2, 4, "ORG"), Span(5, 8, "LOC")]

    tags = encode(spans, length=8, scheme=scheme)

    assert tags == (
        f"{single}-PER",
        "O",
        "B-ORG",
        f"{end}-ORG",
        "O",
        "B-LOC",
        "I-LOC",
        f"{end}-LOC",
    )
    assert decode(tags, scheme=scheme) == tuple(spans)


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [("iobes", "bioes"), ("bioul", "bilou")],
)
def test_explicit_boundary_aliases_match_canonical_scheme(
    alias: _SchemeKey,
    canonical: _SchemeKey,
) -> None:
    spans = [Span(0, 1, "PER"), Span(2, 5, "ORG")]

    expected = encode(spans, length=5, scheme=canonical)
    assert encode(spans, length=5, scheme=alias) == expected
    assert decode(expected, scheme=alias) == tuple(spans)
    assert check_conformance(expected, scheme=alias).conformant


@pytest.mark.parametrize(
    ("scheme", "tags"),
    [
        ("bioes", ["S-PER", "O", "B-ORG", "E-ORG"]),
        ("bioes", ["B-PER", "I-PER", "E-PER", "S-ORG"]),
        ("bilou", ["U-PER", "O", "B-ORG", "L-ORG"]),
        ("bilou", ["B-PER", "I-PER", "L-PER", "U-ORG"]),
    ],
)
def test_strict_conformant_input_reencodes_identically(
    scheme: _SchemeKey,
    tags: list[str],
) -> None:
    assert check_conformance(tags, scheme=scheme).conformant
    spans = decode(tags, scheme=scheme)

    assert encode(spans, length=len(tags), scheme=scheme) == tuple(tags)


@pytest.mark.parametrize(
    ("scheme", "bad_tag"),
    [
        ("bioes", "I-PER"),
        ("bioes", "E-PER"),
        ("bilou", "I-PER"),
        ("bilou", "L-PER"),
    ],
)
def test_explicit_boundary_rejects_invalid_start(
    scheme: _SchemeKey,
    bad_tag: str,
) -> None:
    result = check_conformance([bad_tag], scheme=scheme)

    assert [item.code for item in result.diagnostics] == [DiagnosticCode.INVALID_START]
    assert result.diagnostics[0].index == 0


@pytest.mark.parametrize(
    ("scheme", "tags"),
    [
        ("bioes", ["B-PER", "O"]),
        ("bioes", ["B-PER", "S-ORG"]),
        ("bilou", ["B-PER", "O"]),
        ("bilou", ["B-PER", "U-ORG"]),
    ],
)
def test_explicit_boundary_rejects_premature_open_span_transition(
    scheme: _SchemeKey,
    tags: list[str],
) -> None:
    result = check_conformance(tags, scheme=scheme)

    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.INVALID_TRANSITION
    ]
    assert result.diagnostics[0].index == 1


@pytest.mark.parametrize(
    ("scheme", "tags"),
    [
        ("bioes", ["B-PER", "I-ORG", "E-ORG"]),
        ("bioes", ["B-PER", "E-ORG"]),
        ("bilou", ["B-PER", "I-ORG", "L-ORG"]),
        ("bilou", ["B-PER", "L-ORG"]),
    ],
)
def test_explicit_boundary_rejects_label_mismatch(
    scheme: _SchemeKey,
    tags: list[str],
) -> None:
    result = check_conformance(tags, scheme=scheme)

    assert result.diagnostics[0].code is DiagnosticCode.LABEL_MISMATCH
    assert result.diagnostics[0].index == 1


@pytest.mark.parametrize(
    ("scheme", "tags"),
    [
        ("bioes", ["B-PER"]),
        ("bioes", ["B-PER", "I-PER"]),
        ("bilou", ["B-PER"]),
        ("bilou", ["B-PER", "I-PER"]),
    ],
)
def test_explicit_boundary_rejects_unterminated_span(
    scheme: _SchemeKey,
    tags: list[str],
) -> None:
    result = check_conformance(tags, scheme=scheme)

    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.UNTERMINATED_SPAN
    ]
    assert result.diagnostics[0].index == len(tags) - 1
    assert result.diagnostics[0].next_tag is None


@pytest.mark.parametrize(
    ("scheme", "bad_tag"),
    [("bioes", "L-PER"), ("bilou", "E-PER")],
)
def test_explicit_boundary_rejects_unsupported_state(
    scheme: _SchemeKey,
    bad_tag: str,
) -> None:
    assert (
        check_conformance([bad_tag], scheme=scheme).diagnostics[0].code
        is DiagnosticCode.UNSUPPORTED_MARKER
    )


@pytest.mark.parametrize("scheme", ["bioes", "bilou"])
def test_explicit_boundary_conformance_check_collects_deterministic_diagnostics(
    scheme: _SchemeKey,
) -> None:
    result = check_conformance(["I-PER", "O", "B-ORG"], scheme=scheme)

    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.INVALID_START,
        DiagnosticCode.UNTERMINATED_SPAN,
    ]
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(["I-PER", "O", "B-ORG"], scheme=scheme)
    assert exc_info.value.diagnostics == result.diagnostics
