# spanwend

A Python library for working with sequence-tagging schemes.

Convert between tag sequences and spans, check tag-sequence conformance, and repair malformed tags using explicit policies.
spanwend supports BIO, BILOU, IOB1, and other flat tagging schemes.
Encoding and conversion preserve span boundaries and labels, and report when a target scheme cannot represent them faithfully.

## Table of contents

- [Installation](#installation)
- [Usage](#usage)
- [Related tools](#related-tools)
- [Compatibility and versioning](#compatibility-and-versioning)
- [Acknowledgements](#acknowledgements)
- [Contributing](#contributing)
- [License](#license)

## Installation

`spanwend` requires Python 3.10 or later (see [compatibility and versioning](#compatibility-and-versioning)).
It has no runtime dependencies.

`spanwend` is available from [PyPI](https://pypi.org/project/quirer/).
Install it with your preferred Python package manager.
For example, using `pip`:

```shell
python -m pip install spanwend
```

## Usage

### Quickstart

spanwend uses a collection of [spans](#spans) as its canonical representation.
Tag sequences are thus encoded representations of these spans.

To transform a tag sequence to spans use `decode()`:

```pycon
>>> from spanwend import Span, decode
>>>
>>> tags = ["B-PER", "I-PER", "O", "B-ORG"]
>>> decode(
...     tags,
...     scheme="bio",
... )
(Span(start=0, end=2, label='PER'), Span(start=3, end=4, label='ORG'))

```

`decode()` rejects non-conformant tags with `InvalidTagSequenceError`.
Repairs must be requested explicitly.

To transform spans to a tag sequence use `encode()`:

```pycon
>>> from spanwend import encode
>>>
>>> spans = [(0, 2, "PER"), (3, 4, "ORG")]
>>> encode(
...     spans,
...     length=4,
...     scheme="bio",
... )
('B-PER', 'I-PER', 'O', 'B-ORG')

```

`encode()` raises `UnrepresentableError` when the target scheme cannot preserve the spans.

To convert a tag sequence from one scheme to another use `convert()`:

```pycon
>>> from spanwend import convert
>>>
>>> tags = ["B-PER", "I-PER", "O", "B-ORG"]
>>> convert(
...     tags,
...     source="bio",
...     target="bilou",
... )
('B-PER', 'L-PER', 'O', 'U-ORG')

```

`convert()` raises `UnrepresentableError` when the target scheme cannot preserve the spans.

To repair a tag sequence against a given scheme use `repair()`:

```pycon
>>> from spanwend import repair
>>>
>>> tags = ["O", "I-PER", "I-PER"]
>>> result = repair(
...     tags,
...     scheme="bio",
...     policy="conlleval",
... )
>>> result.tags
('O', 'B-PER', 'I-PER')
>>> result.changed
True
>>> result.diagnostics[0].replacement_tag
'B-PER'

```

Repair currently supports BIO/IOB2 (`"conlleval"`, `"discard"`) and IOB1 (`"conlleval"`).

To check whether a tag sequence conforms to a scheme and inspect diagnostics use `check_conformance()`:

```pycon
>>> from spanwend import check_conformance
>>>
>>> tags = ["I-PER", "I-PER"]
>>> result = check_conformance(
...     tags,
...     scheme="bio",
... )
>>> result.conformant
False
>>> result.diagnostics[0].code
<DiagnosticCode.INVALID_START: 'invalid_start'>

```

To check whether spans can be encoded into a given scheme and inspect any loss use `check_representability()`:

```pycon
>>> from spanwend import check_representability
>>>
>>> spans = [(0, 1, "PER"), (1, 2, "PER")]
>>> result = check_representability(
...     spans,
...     length=2,
...     scheme="io",
... )
>>> result.representable
False
>>> result.code
<RepresentabilityCode.ADJACENT_SAME_LABEL: 'adjacent_same_label'>

```

### Functions

spanwend provides the following functions:

| Function                   | Input                          | Purpose                                            | Output                   |
| :------------------------- | :----------------------------- | :------------------------------------------------- | :----------------------- |
| `decode()`                 | tags                           | transform tags → spans                             | spans                    |
| `encode()`                 | spans                          | transform spans → tags                             | tags                     |
| `convert()`                | tags                           | transform tags → tags                              | tags                     |
| `repair()`                 | tags                           | transform invalid tags → repaired tags             | `RepairResult`           |
| `check_conformance()`      | tags                           | check whether tags conform to a scheme             | `ConformanceResult`      |
| `check_representability()` | spans                          | check whether spans can be represented by a scheme | `RepresentabilityResult` |
| `scheme()`                 | scheme name and syntax options | configure a scheme for repeated operations | `ConfiguredScheme` |

### Configured schemes

For repeated operations, `scheme()` binds a built-in scheme and tag syntax once, producing a `ConfiguredScheme` object.
The six tag and span operations above are available as methods on this object.

```pycon
>>> from spanwend import scheme
>>>
>>> bio = scheme(
...     "bio",
...     separator=":",
...     placement="suffix",
...     outside="_"
... )
>>> bio.decode(["PER:B", "PER:I", "_"])
(Span(start=0, end=2, label='PER'),)
>>> bio.encode([(0, 2, "PER")], length=3)
('PER:B', 'PER:I', '_')

```

### Schemes

Scheme name inputs are case-insensitive. spanwend supports the following schemes:

| Name | Canonical name | Accepted aliases | Non-outside markers | Repair policies |
| --- | --- | --- | --- | --- |
| IO | `io` | — | `I` | — |
| IOB1 | `iob1` | — | `B`, `I` | `conlleval` |
| BIO / IOB2 | `bio` | `iob2` | `B`, `I` | `conlleval`, `discard` |
| IOE1 | `ioe1` | — | `I`, `E` | — |
| IOE2 | `ioe2` | — | `I`, `E` | — |
| BIOS | `bios` | — | `B`, `I`, `S` | — |
| BIOE / BIEO | `bioe` | `bieo` | `B`, `I`, `E` | — |
| IOES | `ioes` | — | `I`, `E`, `S` | — |
| BIOES / IOBES | `bioes` | `iobes` | `B`, `I`, `E`, `S` | — |
| BILOU / BIOUL | `bilou` | `bioul` | `B`, `I`, `L`, `U` | — |
| BMES | `bmes` | — | `B`, `M`, `E`, `S` | — |
| BMEOW / BMEWO | `bmeow` | `bmewo` | `B`, `M`, `E`, `W` | — |

The bare name `"iob"` is rejected because it is ambiguous: use `"iob1"` for IOB1 or `"bio"`/`"iob2"` for BIO/IOB2.

### Spans

spanwend uses a collection of spans as its canonical representation.
A span is a zero-based, right-open interval `[start, end)`, with an optional non-blank string label, where `start` is inclusive and `end` is exclusive.
Span inputs may be any iterable containing the following forms:

- `Span`
- `tuple[int, int]`: `(start, end)`, an unlabelled span
- `tuple[int, int, str | None]`: `(start, end, label)`, where `label is None` for an unlabelled span
- `SpanMapping`: a dictionary with required `start` and `end` integer fields and an optional `label: str | None`

Input spans can be in any order.

Output spans are in ascending `(start, end, label)` order.

All tagging schemes support either labelled or unlabelled spans.
For example, BIO encodes the unlabelled span `(0, 2)` over a length-three sequence to `("B", "I", "O")`.

Labelled and unlabelled spans cannot be mixed in one sequence.

### Tag syntax

Tag syntax is independent of scheme semantics.
Prefix notation is the default, but suffix notation and custom separators/outside tags are supported:

```pycon
>>> from spanwend import TagSyntax, encode
>>>
>>> suffix = TagSyntax(placement="suffix")
>>> spans = [(0, 2, "PER")]
>>> encode(
...     spans,
...     length=3,
...     scheme="bio",
...     syntax=suffix,
... )
('PER-B', 'PER-I', 'O')

```

`DEFAULT_SYNTAX` is `TagSyntax(separator="-", placement="prefix", outside="O")`
and is the default tag syntax used by all string-facing operations.

### Tagging schemes example

Consider the following sentence, in which "Northstar" and "Quanta" are two separate organisations:

```text
Northstar Quanta talks bring Alex Smith to New York City
```

```text
Token               Northstar   Quanta  talks  bring  Alex   Smith   to  New    York   City
Index               0           1       2      3      4      5       6   7      8      9
Entity              ORG         ORG     -      -      PER    PER     -   LOC    LOC    LOC

IO                  <unrepresentable: adjacent ORG spans>
IOB1                I-ORG       B-ORG   O      O      I-PER  I-PER   O   I-LOC  I-LOC  I-LOC
BIO / IOB2          B-ORG       B-ORG   O      O      B-PER  I-PER   O   B-LOC  I-LOC  I-LOC
IOE1                E-ORG       I-ORG   O      O      I-PER  I-PER   O   I-LOC  I-LOC  I-LOC
IOE2                E-ORG       E-ORG   O      O      I-PER  E-PER   O   I-LOC  I-LOC  E-LOC
BIOS                S-ORG       S-ORG   O      O      B-PER  I-PER   O   B-LOC  I-LOC  I-LOC
BIOE / BIEO         B-ORG       B-ORG   O      O      B-PER  E-PER   O   B-LOC  I-LOC  E-LOC
IOES                S-ORG       S-ORG   O      O      I-PER  E-PER   O   I-LOC  I-LOC  E-LOC
BIOES / IOBES       S-ORG       S-ORG   O      O      B-PER  E-PER   O   B-LOC  I-LOC  E-LOC
BILOU / BIOUL       U-ORG       U-ORG   O      O      B-PER  L-PER   O   B-LOC  I-LOC  L-LOC
BMES                S-ORG       S-ORG   O      O      B-PER  E-PER   O   B-LOC  M-LOC  E-LOC
BMEOW / BMEWO       W-ORG       W-ORG   O      O      B-PER  E-PER   O   B-LOC  M-LOC  E-LOC
```

The corresponding canonical spans are:

```python
(
    Span(0, 1, "ORG"),  # Northstar
    Span(1, 2, "ORG"),  # Quanta
    Span(4, 6, "PER"),  # Alex, Smith
    Span(7, 10, "LOC"),  # New, York, City
)
```

The adjacent `ORG` mentions expose the contextual behaviour of IOB1 and IOE1 and also show why these spans are not faithfully representable in IO.
The two- and three-token mentions expose the remaining boundary and middle-token distinctions.

## Related tools

- [`iobes`](https://github.com/blester125/iobes) is another lightweight library for working with sequence-tagging schemes
- [SeqScore](https://github.com/bltlab/seqscore) is an NER/chunking workflow library which includes tools for working with sequence-tagging schemes, including conversion, validation, repair, scoring, and a CLI

## Compatibility and versioning

### Package versioning

This project follows [Semantic Versioning](https://semver.org/).
Releases have version numbers of the form `MAJOR.MINOR.PATCH`:

- **MAJOR** releases may contain backwards-incompatible changes to the public API
- **MINOR** releases may add functionality and deprecate public APIs while remaining backwards compatible
- **PATCH** releases contain backwards-compatible fixes

APIs explicitly documented as experimental are not covered by the same backwards-compatibility guarantees.

For releases before `1.0.0`, the public API should be considered under development and may change between minor releases, as permitted by Semantic Versioning.

### Python-version compatibility

This project supports Python feature releases from their official final release until their official end-of-life (EOL).

Support for a new Python feature release is generally introduced in the first minor release of this project following the upstream Python release.
Python feature releases may be dropped once they reach the end of their upstream support cycle.
The currently supported Python versions are declared in the package metadata.

Dropping an EOL Python version is considered a change to the supported runtime environment rather than a backwards-incompatible change to this project's public API, and therefore does not by itself require a new major release.

## Acknowledgements

This project is developed with assistance from AI coding tools.
All code included in the project is reviewed and tested by [@pdhall99](https://github.com/pdhall99), who takes responsibility for its quality and maintenance.

## Contributing

See the [contributor guide](https://github.com/pdhall99/spanwend/blob/main/docs/CONTRIBUTING.md).

## License

[MIT © PD Hall](https://github.com/pdhall99/spanwend/blob/main/LICENSE)
