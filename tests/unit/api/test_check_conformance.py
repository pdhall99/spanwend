"""Tests for behaviour specific to public `check_conformance()`."""

from dataclasses import FrozenInstanceError

import pytest

from spanwend import (
    DiagnosticCode,
    InvalidTagSequenceError,
    TagSyntax,
    check_conformance,
    decode,
)
from spanwend._scheme.builtins.registry import _SchemeKey


@pytest.mark.parametrize(
    ("scheme", "tags", "expected"),
    [
        ("ioe2", ["X:I", "O"], "continue with LABEL:I or end with LABEL:E"),
        ("ioe2", ["X:I", "BAD:"], "is interrupted before LABEL:E"),
        ("ioe2", ["X:I", "Y:I"], "LABEL:I must match the current span label"),
        ("ioe2", ["X:I", "Y:E"], "LABEL:E must match the current span label"),
        ("ioe2", ["X:I"], "end of the sequence without LABEL:E"),
        ("bilou", ["X:B", "O"], "continue with LABEL:I or end with LABEL:L"),
        (
            "bilou",
            ["X:I"],
            "use LABEL:B for a multi-token span or LABEL:U for a one-token span",
        ),
        ("bilou", ["X:B", "Y:I"], "LABEL:I must match the current span label"),
        ("bilou", ["X:L"], "begin with LABEL:B before LABEL:L"),
        ("bilou", ["X:B", "Y:L"], "LABEL:L must match the current span label"),
        ("bilou", ["X:B"], "end of the sequence without LABEL:L"),
    ],
)
def test_check_conformance_boundary_diagnostic_examples_use_suffix_syntax(
    scheme: _SchemeKey,
    tags: list[str],
    expected: str,
) -> None:
    syntax = TagSyntax(separator=":", placement="suffix")

    result = check_conformance(tags, scheme=scheme, syntax=syntax)

    assert any(expected in diagnostic.message for diagnostic in result.diagnostics)
    assert all("-LABEL" not in diagnostic.message for diagnostic in result.diagnostics)
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme=scheme, syntax=syntax)
    assert exc_info.value.diagnostics == result.diagnostics


def test_check_conformance_boundary_diagnostics_use_multicharacter_separator() -> None:
    result = check_conformance(
        ["I::X"],
        scheme="bioes",
        syntax=TagSyntax(separator="::"),
    )

    assert (
        "use B::LABEL for a multi-token span or S::LABEL for a one-token span"
        in result.diagnostics[0].message
    )


@pytest.mark.parametrize(
    ("scheme", "tags", "expected"),
    [
        ("bioes", ["B"], "open unlabelled span in BIOES/IOBES"),
        ("bioes", ["B"], "end of the sequence without E."),
        ("bioes", ["B", "O"], "continue with I or end with E."),
        ("bioes", ["B", ""], "is interrupted before E."),
        ("bioes", ["I"], "use B for a multi-token span or S for a one-token span"),
        ("bioes", ["E"], "begin with B before E."),
        ("bios", ["B", "O"], "open unlabelled span in BIOS"),
    ],
)
@pytest.mark.parametrize(
    "syntax", [TagSyntax(), TagSyntax(separator=":", placement="suffix")]
)
def test_unlabelled_boundary_diagnostics(
    scheme: _SchemeKey,
    tags: list[str],
    expected: str,
    syntax: TagSyntax,
) -> None:
    result = check_conformance(tags, scheme=scheme, syntax=syntax)

    assert any(expected in diagnostic.message for diagnostic in result.diagnostics)
    assert all(
        "<unlabelled>" not in diagnostic.message and "LABEL" not in diagnostic.message
        for diagnostic in result.diagnostics
    )


def test_diagnostics_preserve_a_literal_unlabelled_label() -> None:
    result = check_conformance(["B-<unlabelled>"], scheme="bioes")

    assert "open '<unlabelled>' span" in result.diagnostics[0].message
    assert "without E-LABEL." in result.diagnostics[0].message


def test_check_conformance_initial_i_is_strict_bio_error_with_actionable_guidance() -> (
    None
):
    result = check_conformance(["I-PER", "I-PER", "O"], scheme="bio")

    assert not result.conformant
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code is DiagnosticCode.INVALID_START
    assert diagnostic.index == 0
    assert diagnostic.tag == "I-PER"
    assert diagnostic.replacement_tag is None
    assert diagnostic.previous_tag is None
    assert diagnostic.next_tag == "I-PER"
    assert "scheme='iob1'" in diagnostic.message
    assert "repair it explicitly" in diagnostic.message


def test_check_conformance_wrong_label_i_without_cascading_matching_i() -> None:
    tags = ["B-PER", "I-ORG", "I-ORG", "O"]
    result = check_conformance(tags, scheme="bio")

    assert [item.code for item in result.diagnostics] == [DiagnosticCode.LABEL_MISMATCH]
    assert result.diagnostics[0].index == 1
    assert result.diagnostics[0].previous_tag == "B-PER"
    assert result.diagnostics[0].next_tag == "I-ORG"


def test_check_conformance_collects_multiple_diagnostics_in_source_order() -> None:
    tags = ["I-PER", "O", "E-ORG", "O", "I-LOC"]
    result = check_conformance(tags, scheme="bio")

    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.INVALID_START,
        DiagnosticCode.UNSUPPORTED_MARKER,
        DiagnosticCode.INVALID_START,
    ]
    assert [item.index for item in result.diagnostics] == [0, 2, 4]


def test_check_conformance_rejects_unsupported_marker() -> None:
    diagnostic = check_conformance(["E-PER"], scheme="bio").diagnostics[0]

    assert diagnostic.code is DiagnosticCode.UNSUPPORTED_MARKER
    assert "not valid in BIO/IOB2" in diagnostic.message


def test_check_conformance_rejects_bare_unknown_marker_semantically() -> None:
    diagnostic = check_conformance(["BPER"], scheme="bio").diagnostics[0]

    assert diagnostic.code is DiagnosticCode.UNSUPPORTED_MARKER
    assert diagnostic.index == 0
    assert diagnostic.tag == "BPER"


def test_check_conformance_rejects_labelled_outside_marker() -> None:
    diagnostic = check_conformance(["O-PER"], scheme="bio").diagnostics[0]

    assert diagnostic.code is DiagnosticCode.OUTSIDE_WITH_LABEL


@pytest.mark.parametrize(
    ("tag", "code"),
    [
        ("-PER", DiagnosticCode.TAG_BLANK_MARKER),
        ("B-", DiagnosticCode.TAG_BLANK_LABEL),
    ],
)
def test_check_conformance_lexical_errors_use_structured_diagnostics(
    tag: str,
    code: DiagnosticCode,
) -> None:
    diagnostic = check_conformance([tag], scheme="bio").diagnostics[0]

    assert diagnostic.code is code
    assert diagnostic.index == 0
    assert diagnostic.tag == tag


def test_conformance_result_and_diagnostics_are_immutable() -> None:
    result = check_conformance(["I-PER"], scheme="bio")

    with pytest.raises(FrozenInstanceError):
        result.diagnostics = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.diagnostics[0].index = 1  # type: ignore[misc]
