from numbers import Integral
from typing import TypeAlias, TypeVar

T = TypeVar("T")

TypeSpec: TypeAlias = type[T] | tuple[type[T], ...]


def _require_instance(
    value: object,
    expected: TypeSpec[T],
    *,
    name: str,
) -> T:
    """Raise if `value` is not an instance of `expected`."""
    types = expected if isinstance(expected, tuple) else (expected,)
    if not isinstance(value, expected):
        expected_names = " or ".join(type_.__name__ for type_ in types)
        raise TypeError(
            f"{name}: expected {expected_names}, got {type(value).__name__}"
        )
    return value


def _require_integer(value: object, *, name: str) -> int:
    """Raise if `value` is not an integer."""
    if not isinstance(value, Integral) or isinstance(value, bool):
        raise TypeError(f"{name}: expected an integer, got {type(value).__name__}")
    return int(value)


def _require_non_blank_string(value: object, *, name: str) -> str:
    """Raise if `value` is a blank string."""
    value = _require_instance(value, str, name=name)
    if _is_blank_string(value):
        raise ValueError(f"{name}: expected a non-blank string")
    return value


def _is_blank_string(value: str) -> bool:
    """Whether a string is blank."""
    return value.strip() == ""
