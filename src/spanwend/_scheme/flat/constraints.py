"""Private first-order transition constraints for flat tagging schemes."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

from spanwend._scheme.flat.semantics import _FlatSemantics
from spanwend._scheme.flat.spec import BoundaryCondition
from spanwend._syntax import _ParsedTag


class _FlatLabelMode(Enum):
    """Label mode fixed for one compiled flat tag alphabet."""

    LABELLED = auto()
    UNLABELLED = auto()


@dataclass(frozen=True, slots=True)
class _FlatTransitionConstraints:
    """First-order validity projection of one flat scheme declaration."""

    semantics: _FlatSemantics
    label_mode: _FlatLabelMode

    def allows_tag(self, tag: _ParsedTag) -> bool:
        """Whether one structured tag belongs to this constraint alphabet."""
        if tag.marker == "O":
            return tag.label is None
        if not self.semantics.supports(tag.marker):
            return False
        if self.label_mode is _FlatLabelMode.LABELLED:
            return tag.label is not None
        return tag.label is None

    def allowed_start(self, tag: _ParsedTag) -> bool:
        """Whether `tag` may occur at the start of a valid sequence."""
        if not self.allows_tag(tag):
            return False
        if tag.marker == "O":
            return True
        return self.semantics.can_start_sequence(tag.marker)

    def allowed_transition(
        self,
        previous: _ParsedTag,
        current: _ParsedTag,
    ) -> bool:
        """Whether `current` may immediately follow `previous`."""
        if not self.allows_tag(previous) or not self.allows_tag(current):
            return False

        if self.semantics.is_contextual_end(previous.marker):
            if (
                current.marker == "O"
                or previous.label != current.label
                or not self.semantics.can_begin(current.marker)
            ):
                return False

        if self.semantics.is_contextual_start(current.marker):
            if previous.marker == "O" or previous.label != current.label:
                return False

        if not self._leaves_open_span(previous, current):
            return current.marker == "O" or self.semantics.can_begin(current.marker)

        must_continue = self.semantics.requires_continuation_after(previous.marker)
        if current.marker == "O":
            return not must_continue

        roles = self.semantics.roles(current.marker)
        if roles.start:
            return not must_continue
        if roles.end:
            if self.semantics.is_contextual_end(current.marker):
                return previous.label == current.label or not must_continue
            return previous.label == current.label
        if roles.singleton:
            return not must_continue

        assert roles.body
        if previous.label == current.label:
            return True
        if self.semantics.requires_start or self.semantics.requires_end:
            return False
        return not must_continue

    def allowed_end(self, tag: _ParsedTag) -> bool:
        """Whether `tag` may occur at the end of a valid sequence."""
        if not self.allows_tag(tag):
            return False
        if tag.marker == "O":
            return True
        return self.semantics.can_end_sequence(tag.marker)

    def accepts(self, tags: Sequence[_ParsedTag]) -> bool:
        """Apply the compiled alphabet, start, pairwise, and end constraints."""
        if not tags:
            return True
        if not self.allowed_start(tags[0]):
            return False
        if any(
            not self.allowed_transition(previous, current)
            for previous, current in zip(tags, tags[1:])
        ):
            return False
        return self.allowed_end(tags[-1])

    def _leaves_open_span(
        self,
        previous: _ParsedTag,
        current: _ParsedTag,
    ) -> bool:
        if previous.marker == "O":
            return False

        roles = self.semantics.roles(previous.marker)
        if roles.end:
            return False
        if roles.singleton:
            return self.semantics.uses_start_role(
                previous.marker,
                current.marker,
            )
        return roles.start or roles.body


def _compile_flat_constraints(
    semantics: _FlatSemantics,
    *,
    label_mode: _FlatLabelMode,
) -> _FlatTransitionConstraints:
    """Compile first-order constraints for one supported flat declaration."""
    _require_first_order_shape(semantics)
    return _FlatTransitionConstraints(semantics=semantics, label_mode=label_mode)


def _require_first_order_shape(semantics: _FlatSemantics) -> None:
    """Reject declaration shapes whose first-order validity is not established."""
    spec = semantics.spec
    contextual_start = (
        spec.start is not None
        and spec.start.condition is BoundaryCondition.ADJACENT_SAME_LABEL
    )
    contextual_end = (
        spec.end is not None
        and spec.end.condition is BoundaryCondition.ADJACENT_SAME_LABEL
    )

    if contextual_start and (spec.end is not None or spec.singleton is not None):
        raise ValueError(
            "Flat constraint compiler has not established first-order validity for "
            "a contextual start combined with end or singleton semantics"
        )
    if contextual_end and (spec.start is not None or spec.singleton is not None):
        raise ValueError(
            "Flat constraint compiler has not established first-order validity for "
            "a contextual end combined with start or singleton semantics"
        )
    if spec.singleton is not None and not (
        semantics.requires_start or semantics.requires_end
    ):
        raise ValueError(
            "Flat constraint compiler has not established first-order validity for "
            "singleton semantics without a required start or end boundary"
        )
