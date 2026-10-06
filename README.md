# scheduleparse

[![Python package](https://github.com/trackIT-Systems/scheduleparse/actions/workflows/python-package.yml/badge.svg)](https://github.com/trackIT-Systems/scheduleparse/actions/workflows/python-package.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/trackIT-Systems/scheduleparse/badges/coverage.json)](https://github.com/trackIT-Systems/scheduleparse/actions/workflows/coverage-badge.yml)
[![Release](https://img.shields.io/github/v/release/trackIT-Systems/scheduleparse)](https://github.com/trackIT-Systems/scheduleparse/releases/latest)

Parse job schedules based on relative start and stop times.

`scheduleparse` is a Python library for defining and working with schedules. It supports absolute times, sunrise/sunset-based times, and recurring patterns with timezone support. Perfect for automation tasks, job scheduling, and time-based system control.

## Features

- **Absolute time schedules**: Define schedules using standard time format (e.g., "09:00", "17:00")
- **Sunrise/sunset-based schedules**: Create schedules relative to sunrise and sunset with offsets (e.g., "sunrise+30m", "sunset-1h")
- **Timezone support**: Schedules are evaluated in their own timezone, whatever timezone the checked time is in, and follow DST changes
- **Overnight schedules**: Support for schedules that span across midnight
- **Recurring schedules**: Skip days feature for every-other-day or custom recurring patterns
- **Active status checking**: Easily determine if a schedule is currently active

## Installation

`scheduleparse` isn't published on PyPI. Install a release from GitHub instead:

```bash
pip install git+https://github.com/trackIT-Systems/scheduleparse.git@2026.10.2
```

Each [release](https://github.com/trackIT-Systems/scheduleparse/releases) also has a wheel and a source archive attached, which you can install directly:

```bash
pip install https://github.com/trackIT-Systems/scheduleparse/releases/download/2026.10.2/scheduleparse-2026.10.2-py3-none-any.whl
```

### Requirements

- Python 3.11 or higher
- `astral>=3.2` (for sunrise/sunset calculations)
- `pytimeparse>=1.1.8` (for flexible time parsing)

## Quick Start

```python
from scheduleparse import ScheduleEntry

# Create a simple daily schedule from 9 AM to 5 PM
schedule = ScheduleEntry("work-hours", "09:00", "17:00")

# Check if the schedule is currently active
if schedule.active():
    print("Schedule is active!")

# Get the next start time
next_start = schedule.next_start()
print(f"Next start: {next_start}")
```

## Time Formats

`start` and `stop` accept:

- **Absolute times** after midnight, parsed by [pytimeparse](https://github.com/wroberts/pytimeparse): `"09:00"`, `"12:00:30"`, `"9h30m"`, `"90m"`. `"24:00"` means midnight at the end of the day.
- **Sun events with an offset**: `<event>+<duration>` or `<event>-<duration>`, where `<event>` is one of `dawn`, `sunrise`, `noon`, `sunset` or `dusk`, and the duration uses the same formats, e.g. `"sunrise+30m"`, `"sunset-1h"`, `"dusk+01:30"`. The offset is required; use `"sunrise+0m"` for sunrise itself. Sun events need a `location`.

A schedule is active from its start (inclusive) until its stop (exclusive). The stop is the first stop time at or after the start, so a stop earlier than the start makes an overnight schedule.

Times are wall-clock times in the schedule's timezone. On days with a DST change a run can be an hour shorter or longer, e.g. `"00:00"`–`"24:00"` lasts 23 hours on the day clocks go forward.

## Usage Examples

### Fixed Time Schedules

Create a schedule with absolute start and stop times:

```python
import datetime
from scheduleparse import ScheduleEntry

# Daily schedule from noon to 1 PM
lunch = ScheduleEntry("lunch-break", "12:00", "13:00", tz=datetime.UTC)

# Check if active at a specific time
now = datetime.datetime(2025, 2, 17, 12, 30, 0, tzinfo=datetime.UTC)
print(lunch.active(now))  # True
```

### Overnight Schedules

Schedules can span across midnight:

```python
import datetime
from scheduleparse import ScheduleEntry

# Night shift: 8 PM to 5 AM
night_shift = ScheduleEntry("night-shift", "20:00", "05:00", tz=datetime.UTC)

# Active during the night
night = datetime.datetime(2025, 2, 17, 3, 0, 0, tzinfo=datetime.UTC)
print(night_shift.active(night))  # True

# Inactive during the day
day = datetime.datetime(2025, 2, 17, 9, 0, 0, tzinfo=datetime.UTC)
print(night_shift.active(day))  # False
```

### Sunrise/Sunset-Based Schedules

Create schedules relative to sunrise and sunset times:

```python
import astral
import zoneinfo
from scheduleparse import ScheduleEntry

# Define location for sunrise/sunset calculations
location = astral.LocationInfo("Berlin", "Germany", "Europe/Berlin", 52.52, 13.405)
tz = zoneinfo.ZoneInfo("Europe/Berlin")

# Active from sunrise to sunset
daytime = ScheduleEntry(
    "daytime",
    "sunrise+00:00",
    "sunset-00:00",
    location=location,
    tz=tz
)

# Active from 30 minutes after sunrise to 1 hour before sunset
adjusted = ScheduleEntry(
    "adjusted-daytime",
    "sunrise+30m",
    "sunset-1h",
    location=location,
    tz=tz
)
```

### Timezone-Aware Schedules

A schedule is evaluated in its own timezone. The time you check can be in any timezone; it is converted first:

```python
import datetime
import zoneinfo
from scheduleparse import ScheduleEntry

# 09:00 to 17:00 New York time
tz = zoneinfo.ZoneInfo("America/New_York")
schedule = ScheduleEntry("ny-schedule", "09:00", "17:00", tz=tz)

# 15:00 UTC is 10:00 in New York
now = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=datetime.UTC)
print(schedule.active(now))  # True
print(schedule.prev_start(now))  # 2025-02-17 09:00:00-05:00
```

Without `tz`, the system timezone is used, including its DST rules. It is read from the `TZ` environment variable, else from `/etc/localtime`. If neither works, the current fixed UTC offset is used and a warning is logged; that offset is wrong after the next DST change. Pass `tz` explicitly to avoid depending on the system configuration.

### Recurring Schedules with Skip Days

Create schedules that run every N days:

```python
import datetime
from scheduleparse import ScheduleEntry

# Every other day (skip 1 day between runs)
every_other_day = ScheduleEntry(
    "bidaily",
    "00:00",
    "24:00",
    skip_days=1,
    tz=datetime.UTC
)

# Every 4 days (skip 3 days between runs)
every_four_days = ScheduleEntry(
    "every-4-days",
    "00:00",
    "24:00",
    skip_days=3,
    tz=datetime.UTC
)

# Use skip_offset to stagger schedules
# This will be active on different days than every_other_day
staggered = ScheduleEntry(
    "bidaily-staggered",
    "00:00",
    "24:00",
    skip_days=1,
    skip_offset=1,
    tz=datetime.UTC
)
```

### Working with Schedule Times

Get previous and next schedule times:

```python
import datetime
from scheduleparse import ScheduleEntry

schedule = ScheduleEntry("daily", "09:00", "17:00", tz=datetime.UTC)
now = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=datetime.UTC)

# Get previous start and stop times
prev_start = schedule.prev_start(now)
prev_stop = schedule.prev_stop(now)
print(f"Previous run: {prev_start} to {prev_stop}")

# Get next start and stop times
next_start = schedule.next_start(now)
next_stop = schedule.next_stop(now)
print(f"Next run: {next_start} to {next_stop}")
```

## API Reference

### `ScheduleEntry`

The main class for defining and working with schedules.

#### Constructor

```python
ScheduleEntry(
    name: str,
    start: str,
    stop: str,
    location: astral.LocationInfo | None = None,
    tz: datetime.tzinfo | None = None,
    skip_days: int = 0,
    skip_offset: int = 0
)
```

**Parameters:**

- `name` (str): A descriptive name for the schedule entry
- `start` (str): Start time, see [Time Formats](#time-formats)
- `stop` (str): Stop time, see [Time Formats](#time-formats)
- `location` (astral.LocationInfo, optional): Location for sunrise/sunset calculations. Required if using sun events
- `tz` (datetime.tzinfo, optional): Timezone the schedule is evaluated in. Defaults to the system timezone (see `local_tz()`)
- `skip_days` (int, optional): Number of days to skip between activations (0 = daily, 1 = every other day, etc.)
- `skip_offset` (int, optional): Offset for skip_days calculation to allow staggered schedules

All methods take an optional, timezone-aware `now` and return datetimes in the schedule's timezone.

#### Methods

##### `active(now: datetime.datetime | None = None) -> bool`

Check if the schedule is currently active.

**Parameters:**
- `now` (datetime.datetime, optional): Reference time. Defaults to current time.

**Returns:** `bool` - True if schedule is active, False otherwise.

##### `prev_start(now: datetime.datetime | None = None) -> datetime.datetime`

Get the timestamp of the schedule's most recent start time.

**Parameters:**
- `now` (datetime.datetime, optional): Reference time. Defaults to current time.

**Returns:** `datetime.datetime` - The timestamp of the previous schedule start.

##### `prev_stop(now: datetime.datetime | None = None) -> datetime.datetime`

Get the stop time of the most recent schedule run.

**Parameters:**
- `now` (datetime.datetime, optional): Reference time. Defaults to current time.

**Returns:** `datetime.datetime` - The timestamp of the previous schedule's stop time.

##### `next_start(now: datetime.datetime | None = None) -> datetime.datetime`

Get the timestamp of the schedule's next start time.

**Parameters:**
- `now` (datetime.datetime, optional): Reference time. Defaults to current time.

**Returns:** `datetime.datetime` - The timestamp of the next schedule start.

##### `next_stop(now: datetime.datetime | None = None) -> datetime.datetime`

Get the stop time of the schedule's next run.

**Parameters:**
- `now` (datetime.datetime, optional): Reference time. Defaults to current time.

**Returns:** `datetime.datetime` - The timestamp of the next schedule's stop time.

### `local_tz() -> datetime.tzinfo`

Get the system timezone including its DST rules, from `TZ` or `/etc/localtime`. Falls back to the current fixed UTC offset and logs a warning.

## Known Limitations

These are documented by expected-failure tests in `tests/test_scheduleparse.py`:

- **`skip_days` restarts every year.** Active days are computed from the day of the year, so the pattern restarts on January 1. For example, with `skip_days=1` there are three days between 2025-12-30 and 2026-01-02.
- **Naive datetimes don't work with `active()`.** It raises `TypeError`. Pass a timezone-aware `now`.
- **Unparseable times mean midnight.** A time string that can't be parsed, such as `"1:30 pm"`, `"sunrise"` without an offset, or a typo, silently resolves to 00:00 instead of raising an error.
- **Large `skip_days` fail.** Values of about 1000 or more raise `RecursionError`. Negative values aren't rejected: `-1` raises `ZeroDivisionError`, and smaller values make the schedule run daily.
- **No sunrise or sunset.** At locations where the sun doesn't rise or set on a given day (polar day or night), sun-based schedules raise `ValueError`.

## Development

Install the project with its development dependencies using [pdm](https://pdm-project.org/):

```bash
pdm install -G dev
```

Run the tests, including the docstring examples, with branch coverage:

```bash
pdm run pytest
```

Run a single test:

```bash
pdm run pytest tests/test_scheduleparse.py::test_fixed
```

Tests are run by CI on every push, on Python 3.11 to 3.14.

### Releasing

Versions use [calendar versioning](https://calver.org/) as `YYYY.MM.MICRO`, where `MICRO` counts the releases within a month. Tags have no `v` prefix.

1. Set `version` in `pyproject.toml`.
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [<version>] - <date>`, add a new empty `## [Unreleased]` section above it, and update the comparison links at the bottom.
3. Commit, then push the commit and the tag:

   ```bash
   git tag <version>
   git push origin main <version>
   ```

The release workflow runs the tests, checks that the tag matches the version in `pyproject.toml`, builds the package and creates a GitHub release. The release notes come from the version's section in the changelog, and the wheel and source archive are attached.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

This project is licensed under the MIT License.
