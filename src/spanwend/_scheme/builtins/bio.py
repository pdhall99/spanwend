"""Private BIO/IOB2 declaration and repair semantics."""

from spanwend._diagnostic import Diagnostic, DiagnosticCode
from spanwend._repair import RepairPolicy, _repair_diagnostic
from spanwend._scheme.flat.codec import build_flat_codec
from spanwend._scheme.flat.spec import Boundary, FlatSchemeSpec
from spanwend._scheme.model import RepairRule, Scheme
from spanwend._syntax import TagSyntax, _ParsedTag

_CODEC = build_flat_codec(
    FlatSchemeSpec(
        start=Boundary("B"),
        body="I",
    ),
    display_name="BIO/IOB2",
    invalid_start_guidance=(
        "If this sequence uses contextual IOB1 tagging, use scheme='iob1'. "
        "If this is malformed BIO output, repair it explicitly."
    ),
)

_REPAIRABLE_CODES = frozenset(
    {DiagnosticCode.INVALID_START, DiagnosticCode.LABEL_MISMATCH}
)


def _repair_bio(
    tags: tuple[str, ...],
    *,
    syntax: TagSyntax,
    policy: RepairPolicy,
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

        if tag.marker == "B":
            repaired.append(raw)
            open_span = True
            open_label = tag.label
            continue

        assert tag.marker == "I"
        if open_span and open_label == tag.label:
            repaired.append(raw)
            continue

        code = (
            DiagnosticCode.INVALID_START
            if not open_span
            else DiagnosticCode.LABEL_MISMATCH
        )
        reason = (
            f"{raw!r} cannot begin a span in BIO/IOB2."
            if not open_span
            else f"{raw!r} cannot continue the open {open_label!r} BIO span."
        )

        if policy is RepairPolicy.CONLLEVAL:
            replacement = syntax._format_checked(_ParsedTag("B", tag.label))
            open_span = True
            open_label = tag.label
        else:
            assert policy is RepairPolicy.DISCARD
            replacement = syntax.outside
            open_span = False
            open_label = None

        repaired.append(replacement)
        diagnostics.append(
            _repair_diagnostic(
                tags,
                index=index,
                code=code,
                reason=reason,
                replacement=replacement,
                policy=policy.value,
            )
        )

    return tuple(repaired), tuple(diagnostics)


def _repair_conlleval(
    tags: tuple[str, ...],
    *,
    syntax: TagSyntax,
) -> tuple[tuple[str, ...], tuple[Diagnostic, ...]]:
    return _repair_bio(tags, syntax=syntax, policy=RepairPolicy.CONLLEVAL)


def _repair_discard(
    tags: tuple[str, ...],
    *,
    syntax: TagSyntax,
) -> tuple[tuple[str, ...], tuple[Diagnostic, ...]]:
    return _repair_bio(tags, syntax=syntax, policy=RepairPolicy.DISCARD)


BIO = Scheme(
    name="bio",
    aliases=("iob2",),
    codec=_CODEC,
    repairs=(
        RepairRule(
            RepairPolicy.CONLLEVAL,
            _repair_conlleval,
            repairable_codes=_REPAIRABLE_CODES,
        ),
        RepairRule(
            RepairPolicy.DISCARD,
            _repair_discard,
            repairable_codes=_REPAIRABLE_CODES,
        ),
    ),
)
