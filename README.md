# scheduleparse

[![Python package](https://github.com/trackIT-Systems/scheduleparse/actions/workflows/python-package.yml/badge.svg)](https://github.com/trackIT-Systems/scheduleparse/actions/workflows/python-package.yml)

Parse job schedules based on relative start and stop times.

`scheduleparse` is a Python library for defining and working with schedules. It supports absolute times, sunrise/sunset-based times, and recurring patterns with timezone support. Perfect for automation tasks, job scheduling, and time-based system control.

## Features

- **Absolute time schedules**: Define schedules using standard time format (e.g., "09:00", "17:00")
- **Sunrise/sunset-based schedules**: Create schedules relative to sunrise and sunset with offsets (e.g., "sunrise+30m", "sunset-1h")
- **Timezone support**: Full timezone awareness for accurate scheduling across different time zones
- **Overnight schedules**: Support for schedules that span across midnight
- **Recurring schedules**: Skip days feature for every-other-day or custom recurring patterns
- **Active status checking**: Easily determine if a schedule is currently active

## Installation

Install using pip:

```bash
pip install scheduleparse
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

Handle schedules across different timezones:

```python
import datetime
import zoneinfo
from scheduleparse import ScheduleEntry

# Schedule in a specific timezone
tz = zoneinfo.ZoneInfo("America/New_York")
schedule = ScheduleEntry("ny-schedule", "09:00", "17:00", tz=tz)

# Check against timezone-aware datetime
now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=tz)
print(schedule.active(now))
```

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
- `start` (str): Start time as "HH:MM" or relative to sunrise/sunset (e.g., "sunrise+30m")
- `stop` (str): Stop time as "HH:MM" or relative to sunrise/sunset
- `location` (astral.LocationInfo, optional): Location for sunrise/sunset calculations. Required if using sunrise/sunset-based times
- `tz` (datetime.tzinfo, optional): Timezone info. Defaults to local timezone if not provided
- `skip_days` (int, optional): Number of days to skip between activations (0 = daily, 1 = every other day, etc.)
- `skip_offset` (int, optional): Offset for skip_days calculation to allow staggered schedules

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

## License

This project is licensed under the MIT License.
