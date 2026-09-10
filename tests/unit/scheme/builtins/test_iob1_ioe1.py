"""Tests for semantics specific to contextual IOB1 and IOE1."""

import pytest

from spanwend import (
    DiagnosticCode,
    InvalidTagSequenceError,
    Span,
    check_conformance,
    check_representability,
    decode,
    encode,
)
from spanwend._scheme.builtins.registry import _SchemeKey


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        ("iob1", ("I-PER", "B-PER")),
        ("ioe1", ("E-PER", "I-PER")),
    ],
)
def test_adjacent_same_label_single_token_spans_use_contextual_marker(
    scheme: _SchemeKey,
    expected: tuple[str, ...],
) -> None:
    spans = [Span(0, 1, "PER"), Span(1, 2, "PER")]

    assert check_representability(spans, length=2, scheme=scheme).representable
    assert encode(spans, length=2, scheme=scheme) == expected
    assert decode(expected, scheme=scheme) == tuple(spans)


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [
        ("iob1", ("I-PER", "I-PER", "B-PER", "I-PER")),
        ("ioe1", ("I-PER", "E-PER", "I-PER", "I-PER")),
    ],
)
def test_adjacent_same_label_multi_token_spans_round_trip(
    scheme: _SchemeKey,
    expected: tuple[str, ...],
) -> None:
    spans = [Span(0, 2, "PER"), Span(2, 4, "PER")]

    assert encode(spans, length=4, scheme=scheme) == expected
    assert decode(expected, scheme=scheme) == tuple(spans)


def test_iob1_rejects_leading_redundant_b() -> None:
    tags = ["B-PER", "I-PER"]
    result = check_conformance(tags, scheme="iob1")

    assert not result.conformant
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code is DiagnosticCode.INVALID_BOUNDARY
    assert diagnostic.index == 0
    assert diagnostic.previous_tag is None
    assert diagnostic.next_tag == "I-PER"
    assert "scheme='bio'/'iob2'" in diagnostic.message

    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="iob1")
    assert exc_info.value.diagnostics == result.diagnostics


@pytest.mark.parametrize(
    "tags",
    [["O", "B-PER"], ["I-PER", "B-ORG"]],
)
def test_iob1_rejects_unneeded_b(tags: list[str]) -> None:
    result = check_conformance(tags, scheme="iob1")

    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.INVALID_BOUNDARY
    ]


def test_iob1_required_b_is_conformant() -> None:
    tags = ["I-PER", "B-PER", "I-PER", "O"]

    assert check_conformance(tags, scheme="iob1").conformant
    assert decode(tags, scheme="iob1") == (
        Span(0, 1, "PER"),
        Span(1, 3, "PER"),
    )


def test_ioe1_rejects_redundant_terminal_e_with_right_context() -> None:
    tags = ["I-PER", "E-PER"]
    result = check_conformance(tags, scheme="ioe1")

    assert not result.conformant
    diagnostic = result.diagnostics[0]
    assert diagnostic.code is DiagnosticCode.INVALID_BOUNDARY
    assert diagnostic.index == 1
    assert diagnostic.previous_tag == "I-PER"
    assert diagnostic.next_tag is None
    assert "scheme='ioe2'" in diagnostic.message

    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="ioe1")
    assert exc_info.value.diagnostics == result.diagnostics


@pytest.mark.parametrize(
    ("tags", "next_tag"),
    [
        (["E-PER", "O"], "O"),
        (["E-PER", "I-ORG"], "I-ORG"),
    ],
)
def test_ioe1_rejects_unneeded_e(tags: list[str], next_tag: str) -> None:
    diagnostic = check_conformance(tags, scheme="ioe1").diagnostics[0]

    assert diagnostic.code is DiagnosticCode.INVALID_BOUNDARY
    assert diagnostic.next_tag == next_tag


def test_ioe1_required_e_is_conformant() -> None:
    tags = ["I-PER", "E-PER", "I-PER", "O"]

    assert check_conformance(tags, scheme="ioe1").conformant
    assert decode(tags, scheme="ioe1") == (
        Span(0, 2, "PER"),
        Span(2, 3, "PER"),
    )


def test_ioe1_chain_of_adjacent_same_label_singletons() -> None:
    tags = ["E-PER", "E-PER", "I-PER"]

    assert check_conformance(tags, scheme="ioe1").conformant
    assert decode(tags, scheme="ioe1") == (
        Span(0, 1, "PER"),
        Span(1, 2, "PER"),
        Span(2, 3, "PER"),
    )


@pytest.mark.parametrize(
    ("scheme", "tags"),
    [
        ("iob1", ["I-PER", "I-PER", "O", "I-ORG"]),
        ("iob1", ["I-PER", "B-PER", "I-PER"]),
        ("ioe1", ["I-PER", "I-PER", "O", "I-ORG"]),
        ("ioe1", ["I-PER", "E-PER", "I-PER"]),
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
    [("iob1", "E-PER"), ("ioe1", "B-PER")],
)
def test_contextual_schemes_reject_unsupported_markers(
    scheme: _SchemeKey,
    bad_tag: str,
) -> None:
    result = check_conformance([bad_tag], scheme=scheme)

    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.UNSUPPORTED_MARKER
    ]


def test_iob1_conformance_check_continues_deterministically_after_invalid_b() -> None:
    tags = ["B-PER", "I-PER", "O", "B-ORG", "I-ORG"]
    result = check_conformance(tags, scheme="iob1")

    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.INVALID_BOUNDARY,
        DiagnosticCode.INVALID_BOUNDARY,
    ]
    assert [item.index for item in result.diagnostics] == [0, 3]


def test_ioe1_conformance_check_continues_deterministically_after_invalid_e() -> None:
    tags = ["E-PER", "O", "E-ORG"]
    result = check_conformance(tags, scheme="ioe1")

    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.INVALID_BOUNDARY,
        DiagnosticCode.INVALID_BOUNDARY,
    ]
    assert [item.index for item in result.diagnostics] == [0, 2]
