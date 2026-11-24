# Changelog

## [Unreleased]

## [0.2.0] - 2026-11-24

### Added

- Support for Python 3.15
- `Import-Name` package metadata ([PEP 794](https://peps.python.org/pep-0794/)), declaring `spanwend` as the import name

### Changed

- `DiagnosticCode`, `RepairPolicy` and `RepresentabilityCode` are now `StrEnum`s, so `str()` and f-strings give a member's value, such as `conlleval`, rather than its name, such as `RepairPolicy.CONLLEVAL`

### Removed

- Support for Python 3.10, making Python 3.11 the minimum supported version

## [0.1.1] - 2026-09-24

### Changed

- Package description

### Fixed

- Incorrect PyPI link in README

## [0.1.0] - 2026-09-10

### Added

- Initial public release

[Unreleased]: https://github.com/pdhall99/spanwend/compare/0.2.0...HEAD
[0.2.0]: https://github.com/pdhall99/spanwend/compare/0.1.1..0.2.0
[0.1.1]: https://github.com/pdhall99/spanwend/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/pdhall99/spanwend/releases/tag/0.1.0
