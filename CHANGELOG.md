# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [calendar versioning](https://calver.org/) in the form `YYYY.MM.MICRO` (e.g. `2025.10.1`), where `MICRO` counts the releases within a month.

## [Unreleased]

## [2026.10.2] - 2026-10-06

### Fixed

- A bare sun event without an offset (e.g. `sunrise`, `sunset`) resolves to that event. Previously it was read as an unparseable absolute time and silently resolved to midnight; only `sunrise+00:00` worked.

## [2026.10.1] - 2026-10-06

### Fixed

- Schedules are evaluated in the schedule's timezone. Previously the calendar day was taken from `now` in whatever timezone it was passed, so a Berlin schedule like `00:01`–`01:00` checked with a UTC timestamp resolved to the previous day and never became active ([trackIT-Systems/wittypi4#9](https://github.com/trackIT-Systems/wittypi4/issues/9)).
- Without an explicit `tz`, the system timezone is now used including its DST rules (from `TZ`, else `/etc/localtime`). Previously the fixed UTC offset at construction time was used, so long-running processes were off by one hour after a DST change.

### Added

- `local_tz()` to resolve the system timezone with its DST rules.
- This changelog.
- Tests for all sun events (`dawn`, `sunrise`, `noon`, `sunset`, `dusk`) and offset formats, DST transitions, and consistency of `prev_*`/`next_*`/`active()`; 100% line and branch coverage.
- Known bugs are documented as expected-failure tests: `skip_days` gap at the turn of the year, `active()` with a naive datetime, unparseable times resolving to midnight, `RecursionError` for large `skip_days`, and unvalidated negative `skip_days`.

### Changed

- Docstring examples are run as doctests.
- CI runs on every push and tests Python 3.11–3.14.
- Releases are created by CI on tag push: tests run first, then the package is built and attached to a GitHub release with the notes from this changelog.

## [2025.10.1] - 2025-10-20

### Added

- Docstrings for the public API and an extended README with usage examples.
- Extensive tests for edge cases, overnight and sunrise/sunset schedules, and `skip_days`/`skip_offset` combinations.

## [2025.2.2] - 2025-02-17

### Fixed

- `skip_offset` shifted the active days in the wrong direction.

## [2025.2.1] - 2025-02-17

Initial release.

### Added

- `ScheduleEntry` with absolute start and stop times (`"09:00"`) and times relative to sunrise and sunset (`"sunrise+30m"`, `"sunset-1h"`), including overnight schedules.
- `active()`, `prev_start()`, `prev_stop()`, `next_start()` and `next_stop()`.
- `skip_days` for recurring schedules and `skip_offset` to stagger them.
- Timezone support via the `tz` argument.
- Requires Python 3.11 or newer.

[Unreleased]: https://github.com/trackIT-Systems/scheduleparse/compare/2026.10.2...HEAD
[2026.10.2]: https://github.com/trackIT-Systems/scheduleparse/compare/2026.10.1...2026.10.2
[2026.10.1]: https://github.com/trackIT-Systems/scheduleparse/compare/2025.10.1...2026.10.1
[2025.10.1]: https://github.com/trackIT-Systems/scheduleparse/compare/2025.2.2...2025.10.1
[2025.2.2]: https://github.com/trackIT-Systems/scheduleparse/compare/2025.2.1...2025.2.2
[2025.2.1]: https://github.com/trackIT-Systems/scheduleparse/releases/tag/2025.2.1
