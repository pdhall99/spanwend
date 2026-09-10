"""Tests for public exception serialization."""

import pickle

import pytest

from spanwend import InvalidTagSequenceError, UnrepresentableError, decode, encode


def test_invalid_tag_sequence_error_pickle_round_trip() -> None:
    with pytest.raises(InvalidTagSequenceError) as exc_info:
        decode(["I-PER", "O", "I-ORG"], scheme="bio")

    original = exc_info.value
    restored = pickle.loads(pickle.dumps(original))

    assert type(restored) is InvalidTagSequenceError
    assert restored.diagnostics == original.diagnostics
    assert restored.args == original.args
    assert str(restored) == str(original)


def test_unrepresentable_error_pickle_round_trip() -> None:
    with pytest.raises(UnrepresentableError) as exc_info:
        encode([(0, 1), (1, 2)], length=2, scheme="io")

    original = exc_info.value
    restored = pickle.loads(pickle.dumps(original))

    assert type(restored) is UnrepresentableError
    assert restored.code is original.code
    assert restored.message == original.message
    assert restored.args == original.args
    assert str(restored) == str(original)
