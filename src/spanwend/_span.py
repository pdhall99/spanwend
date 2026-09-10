"""Canonical span value."""

from dataclasses import dataclass
from typing import Protocol, TypeVar

from spanwend._check import _require_integer, _require_non_blank_string

_T_co = TypeVar("_T_co", covariant=True)
_T = TypeVar("_T")


class _Sliceable(Protocol[_T_co]):
    def __getitem__(self, key: slice, /) -> _T_co: ...


@dataclass(frozen=True, slots=True)
class Span:
    """A labelled or unlabelled zero-based right-open interval `[start, end)`.

    For example:
    ```text
    [2, 6)

            start=2         end=6
              |               |
              v               v
      +---+---+---+---+---+---+---+---+---+
      | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
      +---+---+---+---+---+---+---+---+---+
              |               |
              +---------------+

              covers 2, 3, 4, 5
              length = 6 - 2 = 4
    ```

    Attributes:
        start: Inclusive start position. A non-negative integer.
        end: Exclusive end position. An integer greater than `start`.
        label: Non-blank string label, or `None` for an unlabelled span.
            Defaults to `None`.
    """

    start: int
    end: int
    label: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the intrinsic span value."""
        start = _require_integer(self.start, name="Span.start")
        end = _require_integer(self.end, name="Span.end")

        if start < 0:
            raise ValueError(
                f"Span.start: expected a non-negative value, got {start!r}"
            )
        if end <= start:
            raise ValueError(
                f"Span.end: expected a value greater than start ({start}), got {end}"
            )

        if self.label is not None:
            try:
                _require_non_blank_string(self.label, name="Span.label")
            except TypeError:
                raise TypeError(
                    "Span.label: expected a non-blank string or None, "
                    f"got {type(self.label).__name__}"
                ) from None
            except ValueError:
                raise ValueError(
                    "Span.label: expected a non-blank string or None, "
                    f"got {self.label!r}"
                ) from None

        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    def extract(self, values: _Sliceable[_T]) -> _T:
        """Return the values covered by this span.

        Args:
            values: Values indexed using the same offsets as the span.

        Returns:
            The slice of `values` from `start` up to, but not including, `end`.

        Examples:
            ```pycon
            >>> Span(1, 3, "PER").extract(["A", "B", "C", "D"])
            ['B', 'C']
            >>> Span(0, 4, "PER").extract("John Smith")
            'John'
            >>> Span(0, 2, "LOC").extract(("New", "York", "City"))
            ('New', 'York')

            ```
        """
        return values[self.start : self.end]

    def _sort_key(self) -> tuple[int, int, str | None]:
        """Return the `(start, end, label)` projection used for canonical ordering."""
        return self.start, self.end, self.label
