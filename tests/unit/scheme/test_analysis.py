"""Tests for shared tag-sequence analysis semantics."""

import pytest

from spanwend import DiagnosticCode, InvalidTagSequenceError, check_conformance, decode


@pytest.mark.parametrize(
    "tags",
    [
        ("B-PER", "I-PER", "O", "B", "I"),
        ("B", "I", "O", "B-PER", "I-PER"),
        ("B-PER", "I"),
        ("B", "I-PER"),
    ],
)
def test_tag_sequences_reject_mixed_label_modes(tags: tuple[str, ...]) -> None:
    result = check_conformance(tags, scheme="bio")

    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        DiagnosticCode.MIXED_LABEL_MODE
    ]
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(tags, scheme="bio")
    assert exc_info.value.diagnostics == result.diagnostics
