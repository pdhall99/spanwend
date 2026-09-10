"""Differential checks against iobes and SeqScore on shared valid domains.

The comparison libraries are test-only references. Differences are investigation
signals rather than authority: spanwend's design and published scheme semantics
remain the specification.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest

from spanwend import Span, decode
from spanwend._scheme.builtins.registry import _SchemeKey
from tests.conformance._conformance import reference_encode, reference_is_representable

FIXTURES = (
    (4, [Span(0, 2, "PER"), Span(3, 4, "ORG")]),
    (3, [Span(0, 1, "PER"), Span(1, 3, "PER")]),
    (3, [Span(0, 1, "PER"), Span(1, 2, "ORG")]),
)


def _span_triples(items: Any) -> list[tuple[int, int, str]]:
    """Normalize external span/mention objects to spanwend semantics."""
    triples: list[tuple[int, int, str]] = []
    for item in items:
        if hasattr(item, "span"):
            triples.append((item.span.start, item.span.end, item.type))
        else:
            triples.append((item.start, item.end, item.type))
    return triples


@pytest.mark.parametrize(
    "scheme",
    ("iob1", "bio", "bioes", "bilou", "bmeow"),
)
@pytest.mark.parametrize(("length", "spans"), FIXTURES)
def test_iobes_matches_shared_default_syntax_domain(
    scheme: _SchemeKey,
    length: int,
    spans: list[Span],
) -> None:
    """Compare the strict-valid shared schemes with iobes 1.5.1."""
    iobes = pytest.importorskip("iobes", reason="iobes is a test-only dependency")
    expected_tags = reference_encode(spans, length=length, scheme=scheme)

    parse_name = {
        "iob1": "parse_spans_iob",
        "bio": "parse_spans_bio",
        "bioes": "parse_spans_iobes",
        "bilou": "parse_spans_bilou",
        "bmeow": "parse_spans_bmeow",
    }[scheme]
    write_name = {
        "iob1": "write_iob_tags",
        "bio": "write_bio_tags",
        "bioes": "write_iobes_tags",
        "bilou": "write_bilou_tags",
        "bmeow": "write_bmeow_tags",
    }[scheme]

    external_decoded = getattr(iobes, parse_name)(expected_tags)
    assert _span_triples(external_decoded) == [
        (span.start, span.end, span.label) for span in spans
    ]
    assert decode(expected_tags, scheme=scheme) == tuple(spans)

    external_spans = [
        iobes.Span(
            span.label,
            span.start,
            span.end,
            tuple(range(span.start, span.end)),
        )
        for span in spans
    ]
    assert (
        tuple(getattr(iobes, write_name)(external_spans, length=length))
        == expected_tags
    )


@pytest.mark.parametrize(
    "scheme",
    ("io", "iob1", "bio", "bioes", "bilou", "bmes", "bmeow"),
)
@pytest.mark.parametrize(("length", "spans"), FIXTURES)
def test_seqscore_matches_shared_default_syntax_domain(
    scheme: _SchemeKey,
    length: int,
    spans: list[Span],
) -> None:
    """Compare strict-valid shared schemes with SeqScore 0.9.0."""
    pytest.importorskip("seqscore", reason="SeqScore is a test-only dependency")
    encoding_module = import_module("seqscore.encoding")
    model_module = import_module("seqscore.model")

    if scheme == "bilou":
        encoding = encoding_module.BIOES(encoding_module.BILOUDialect())
    elif scheme == "bmes":
        encoding = encoding_module.BIOES(encoding_module.BMESDialect())
    elif scheme == "bmeow":
        encoding = encoding_module.BIOES(encoding_module.BMEOWDialect())
    else:
        dialect = encoding_module.BIOESDialect()
        encoding_type = {
            "io": encoding_module.IO,
            "iob1": encoding_module.IOB,
            "bio": encoding_module.BIO,
            "bioes": encoding_module.BIOES,
        }[scheme]
        encoding = encoding_type(dialect)

    if not reference_is_representable(spans, length=length, scheme=scheme):
        pytest.skip("fixture is outside the scheme shared lossless domain")

    expected_tags = reference_encode(spans, length=length, scheme=scheme)
    external_decoded = encoding.decode_labels(expected_tags)
    assert _span_triples(external_decoded) == [
        (span.start, span.end, span.label) for span in spans
    ]
    assert decode(expected_tags, scheme=scheme) == tuple(spans)

    external_mentions = [
        model_module.Mention(
            model_module.Span(span.start, span.end),
            span.label,
        )
        for span in spans
    ]
    assert tuple(encoding.encode_mentions(external_mentions, length)) == expected_tags
