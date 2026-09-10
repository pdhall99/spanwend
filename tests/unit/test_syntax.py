"""Tests for tag syntax parsing and formatting."""

from dataclasses import FrozenInstanceError

import pytest

from spanwend import DEFAULT_SYNTAX, TagSyntax
from spanwend._syntax import _ParsedTag, _TagParseError


def test_default_syntax() -> None:
    assert DEFAULT_SYNTAX == TagSyntax("-", "prefix", "O")


def test_prefix_syntax_round_trip() -> None:
    tag = _ParsedTag("B", "PER")

    assert DEFAULT_SYNTAX._parse(DEFAULT_SYNTAX._format(tag)) == tag


def test_suffix_syntax_round_trip() -> None:
    syntax = TagSyntax(placement="suffix")
    tag = _ParsedTag("I", "ORG")

    assert syntax._format(tag) == "ORG-I"
    assert syntax._parse("ORG-I") == tag


def test_unlabelled_round_trip() -> None:
    tag = _ParsedTag("B", None)

    assert DEFAULT_SYNTAX._format(tag) == "B"
    assert DEFAULT_SYNTAX._parse("B") == tag
    assert TagSyntax(placement="suffix")._format(tag) == "B"


def test_label_equal_to_default_outside_marker_is_unambiguous() -> None:
    assert DEFAULT_SYNTAX._parse("I-O") == _ParsedTag("I", "O")

    suffix = TagSyntax(placement="suffix")
    assert suffix._parse("O-I") == _ParsedTag("I", "O")


def test_prefix_label_may_contain_separator() -> None:
    assert DEFAULT_SYNTAX._parse("B-ORG-COMPANY") == _ParsedTag("B", "ORG-COMPANY")


def test_suffix_label_may_contain_separator() -> None:
    syntax = TagSyntax(placement="suffix")

    assert syntax._parse("ORG-COMPANY-B") == _ParsedTag("B", "ORG-COMPANY")


@pytest.mark.parametrize("tag", ["B-", "-PER", ""])
def test_malformed_tag_is_rejected(tag: str) -> None:
    with pytest.raises(_TagParseError):
        DEFAULT_SYNTAX._parse(tag)


def test_tag_syntax_is_immutable() -> None:
    syntax = TagSyntax()

    with pytest.raises(FrozenInstanceError):
        syntax.separator = ":"  # type: ignore[misc]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"separator": ""},
        {"placement": "middle"},
        {"outside": ""},
    ],
)
def test_invalid_tag_syntax_configuration_is_rejected(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        TagSyntax(**kwargs)  # type: ignore[arg-type]
