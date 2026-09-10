"""Private contextual IOB1 declaration and repair semantics."""

from spanwend._diagnostic import Diagnostic, DiagnosticCode
from spanwend._repair import RepairPolicy, _repair_diagnostic
from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, BoundaryCondition, FlatSchemeSpec
from spanwend._scheme.model import RepairRule, Scheme
from spanwend._syntax import TagSyntax, _ParsedTag

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        start=Boundary("B", BoundaryCondition.ADJACENT_SAME_LABEL),
        body="I",
    ),
    display_name="IOB1",
    invalid_boundary_guidance=(
        "If every span begins with B, use scheme='bio'/'iob2' instead."
    ),
)


def _repair_conlleval(
    tags: tuple[str, ...],
    *,
    syntax: TagSyntax,
) -> tuple[tuple[str, ...], tuple[Diagnostic, ...]]:
    repaired: list[str] = []
    diagnostics: list[Diagnostic] = []
    open_span = False
    open_label: str | None = None

    for index, raw in enumerate(tags):
        tag = syntax._parse(raw)

        if tag.marker == "O":
            repaired.append(raw)
            open_span = False
            open_label = None
            continue

        if tag.marker == "I":
            repaired.append(raw)
            open_span = True
            open_label = tag.label
            continue

        assert tag.marker == "B"
        if open_span and open_label == tag.label:
            repaired.append(raw)
            open_label = tag.label
            continue

        replacement = syntax._format_checked(_ParsedTag("I", tag.label))
        repaired.append(replacement)
        diagnostics.append(
            _repair_diagnostic(
                tags,
                index=index,
                code=DiagnosticCode.INVALID_BOUNDARY,
                reason=(
                    f"{raw!r} is not required at this position in IOB1; B is "
                    "reserved for adjacent same-label span boundaries."
                ),
                replacement=replacement,
                policy=RepairPolicy.CONLLEVAL.value,
            )
        )
        open_span = True
        open_label = tag.label

    return tuple(repaired), tuple(diagnostics)


IOB1 = Scheme(
    name="iob1",
    aliases=(),
    codec=_CODEC,
    repairs=(
        RepairRule(
            RepairPolicy.CONLLEVAL,
            _repair_conlleval,
            repairable_codes=frozenset({DiagnosticCode.INVALID_BOUNDARY}),
        ),
    ),
)
