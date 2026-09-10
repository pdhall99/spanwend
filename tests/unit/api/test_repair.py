"""Tests for behaviour specific to the public `repair()` operation."""

import pytest

from spanwend import (
    DiagnosticCode,
    InvalidTagSequenceError,
    RepairPolicy,
    RepairResult,
    TagSyntax,
    check_conformance,
    decode,
    repair,
)
from spanwend._scheme.builtins.registry import _SchemeKey


def assert_repair_postcondition(
    result: RepairResult,
    *,
    scheme: _SchemeKey,
    syntax: TagSyntax = TagSyntax(),
) -> None:
    assert all(
        diagnostic.replacement_tag == result.tags[diagnostic.index]
        for diagnostic in result.diagnostics
    )
    assert check_conformance(result.tags, scheme=scheme, syntax=syntax).conformant
    decode(result.tags, scheme=scheme, syntax=syntax)


def test_repair_valid_bio_is_unchanged() -> None:
    tags = ["B-PER", "I-PER", "O", "B-ORG"]
    result = repair(tags, scheme="bio", policy="conlleval")

    assert result.tags == tuple(tags)
    assert result.diagnostics == ()
    assert result.changed is False
    assert_repair_postcondition(result, scheme="bio")


def test_bio_conlleval_repairs_initial_i_as_new_chunk() -> None:
    result = repair(["I-PER", "I-PER"], scheme="bio", policy="conlleval")

    assert result.tags == ("B-PER", "I-PER")
    assert result.changed is True
    assert [item.code for item in result.diagnostics] == [DiagnosticCode.INVALID_START]
    assert "'B-PER'" in result.diagnostics[0].message
    assert_repair_postcondition(result, scheme="bio")


def test_bio_conlleval_repairs_label_mismatch_as_new_chunk() -> None:
    result = repair(
        ["B-PER", "I-ORG", "I-ORG"],
        scheme="bio",
        policy=RepairPolicy.CONLLEVAL,
    )

    assert result.tags == ("B-PER", "B-ORG", "I-ORG")
    assert [item.code for item in result.diagnostics] == [DiagnosticCode.LABEL_MISMATCH]
    assert_repair_postcondition(result, scheme="bio")


def test_bio_discard_cascades_against_repaired_state() -> None:
    result = repair(["I-PER", "I-PER"], scheme="bio", policy="discard")

    assert result.tags == ("O", "O")
    assert result.changed is True
    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.INVALID_START,
        DiagnosticCode.INVALID_START,
    ]
    assert_repair_postcondition(result, scheme="bio")


def test_bio_discard_repairs_multiple_transition_errors() -> None:
    result = repair(
        ["B-PER", "I-ORG", "I-ORG", "B-LOC", "I-PER"],
        scheme="bio",
        policy="discard",
    )

    assert result.tags == ("B-PER", "O", "O", "B-LOC", "O")
    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.LABEL_MISMATCH,
        DiagnosticCode.INVALID_START,
        DiagnosticCode.LABEL_MISMATCH,
    ]
    assert_repair_postcondition(result, scheme="bio")


def test_repair_diagnostics_retain_source_context() -> None:
    result = repair(
        ["O", "I-PER", "B-ORG"],
        scheme="bio",
        policy="conlleval",
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.index == 1
    assert diagnostic.tag == "I-PER"
    assert diagnostic.replacement_tag == "B-PER"
    assert diagnostic.previous_tag == "O"
    assert diagnostic.next_tag == "B-ORG"
    assert "conlleval" in diagnostic.message
    assert "B-PER" in diagnostic.message


def test_iob1_conlleval_repairs_redundant_initial_b() -> None:
    result = repair(
        ["B-PER", "I-PER"],
        scheme="iob1",
        policy="conlleval",
    )

    assert result.tags == ("I-PER", "I-PER")
    assert [item.code for item in result.diagnostics] == [
        DiagnosticCode.INVALID_BOUNDARY
    ]
    assert_repair_postcondition(result, scheme="iob1")


def test_iob1_conlleval_preserves_required_b() -> None:
    tags = ["I-PER", "B-PER"]
    result = repair(tags, scheme="iob1", policy="conlleval")

    assert result.tags == tuple(tags)
    assert result.changed is False
    assert result.diagnostics == ()
    assert_repair_postcondition(result, scheme="iob1")


def test_iob1_conlleval_repairs_different_label_b_to_i() -> None:
    result = repair(
        ["I-PER", "B-ORG", "I-ORG"],
        scheme="iob1",
        policy="conlleval",
    )

    assert result.tags == ("I-PER", "I-ORG", "I-ORG")
    assert_repair_postcondition(result, scheme="iob1")


@pytest.mark.parametrize(
    ("scheme", "tags", "expected", "code"),
    [
        ("bio", ("I", "I"), ("B", "I"), DiagnosticCode.INVALID_START),
        ("iob1", ("B", "I"), ("I", "I"), DiagnosticCode.INVALID_BOUNDARY),
    ],
)
def test_repair_preserves_unlabelled_mode(
    scheme: _SchemeKey,
    tags: tuple[str, ...],
    expected: tuple[str, ...],
    code: DiagnosticCode,
) -> None:
    result = repair(tags, scheme=scheme, policy="conlleval")

    assert result.tags == expected
    assert [diagnostic.code for diagnostic in result.diagnostics] == [code]
    assert_repair_postcondition(result, scheme=scheme)


@pytest.mark.parametrize("scheme", ["io", "ioe1", "bioes", "bilou"])
def test_conlleval_rejects_unsupported_schemes(scheme: _SchemeKey) -> None:
    with pytest.raises(ValueError, match="not supported"):
        repair([], scheme=scheme, policy="conlleval")


def test_discard_is_only_supported_for_bio() -> None:
    with pytest.raises(ValueError, match="not supported"):
        repair(["I-PER"], scheme="iob1", policy="discard")


def test_unknown_repair_policy_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="policy: expected one of"):
        repair(
            [],
            scheme="bio",
            policy="best_effort",  # type: ignore[bad-argument-type]
        )


def test_non_string_repair_policy_fails_explicitly() -> None:
    with pytest.raises(TypeError, match="policy: expected RepairPolicy or str"):
        repair([], scheme="bio", policy=object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tags",
    [
        ["B-"],
        ["BANANA"],
        ["X-PER"],
        ["O-PER"],
    ],
)
def test_bio_repair_refuses_inputs_outside_declared_domain(tags: list[str]) -> None:
    with pytest.raises(InvalidTagSequenceError):
        repair(tags, scheme="bio", policy="conlleval")


def test_bio_repair_supports_suffix_syntax() -> None:
    syntax = TagSyntax(placement="suffix")
    result = repair(
        ["PER-I", "PER-I", "O"],
        scheme="bio",
        policy="conlleval",
        syntax=syntax,
    )

    assert result.tags == ("PER-B", "PER-I", "O")
    assert_repair_postcondition(result, scheme="bio", syntax=syntax)


def test_bio_repair_supports_custom_separator_and_outside() -> None:
    syntax = TagSyntax(separator="::", outside="OUT")
    result = repair(
        ["OUT", "I::PER", "I::PER"],
        scheme="bio",
        policy="conlleval",
        syntax=syntax,
    )

    assert result.tags == ("OUT", "B::PER", "I::PER")
    assert_repair_postcondition(result, scheme="bio", syntax=syntax)
