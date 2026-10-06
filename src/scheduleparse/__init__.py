"""Parse job schedules based on relative start and stop times.

This module provides the ScheduleEntry class for defining and working with
schedules that can use absolute times, sunrise/sunset-based times, and
recurring patterns with timezone support.

Example:
    >>> from scheduleparse import ScheduleEntry
    >>> schedule = ScheduleEntry("daily-job", "09:00", "17:00")
    >>> schedule.active()  # Check if currently active  # doctest: +SKIP
    False
"""

import datetime
import importlib.metadata
import logging
import os
import zoneinfo

import astral
import astral.sun
import pytimeparse

__version__ = importlib.metadata.version(__name__)

logger = logging.getLogger(__name__)

# events returned by astral.sun.sun() that can be used as schedule times
SUN_EVENTS = ("dawn", "sunrise", "noon", "sunset", "dusk")


def local_tz() -> datetime.tzinfo:
    """Get the system timezone including its DST rules.

    Uses the TZ environment variable, else /etc/localtime. Falls back to the current
    fixed UTC offset, which is wrong after the next DST change.
    """
    try:
        key = os.environ.get("TZ", "").lstrip(":")
        if key:
            return zoneinfo.ZoneInfo(key)
        with open("/etc/localtime", "rb") as f:
            return zoneinfo.ZoneInfo.from_file(f, key="localtime")
    except (OSError, ValueError, zoneinfo.ZoneInfoNotFoundError):
        logger.warning("Couldn't determine system timezone, using fixed UTC offset")
        return datetime.datetime.now().astimezone().tzinfo


class ScheduleEntry:
    """Represents a schedule with start and stop times.

    A schedule entry defines when a job or task should be active. Times can be
    specified as absolute times (e.g., "12:00") or relative to sunrise/sunset
    (e.g., "sunrise+30m", "sunset-1h"). Supports recurring schedules with skip
    days and timezone-aware calculations.

    Args:
        name: A descriptive name for the schedule entry.
        start: Start time as a string. Can be absolute time ("HH:MM") or relative
            to sunrise/sunset ("sunrise+30m", "sunset-1h").
        stop: Stop time as a string. Can be absolute time ("HH:MM") or relative
            to sunrise/sunset. Can extend past midnight for overnight schedules.
        location: Optional astral.LocationInfo for sunrise/sunset calculations.
            Required if using sunrise/sunset-based times.
        tz: Timezone info. Defaults to local timezone if not provided.
        skip_days: Number of days to skip between activations. 0 means daily,
            1 means every other day, etc.
        skip_offset: Offset for skip_days calculation to allow staggered schedules.

    Example:
        >>> # Simple daily schedule from 9 AM to 5 PM
        >>> schedule = ScheduleEntry("work", "09:00", "17:00")
        >>> schedule.active()  # doctest: +SKIP
        True

        >>> # Sunrise to sunset schedule
        >>> import astral
        >>> import zoneinfo
        >>> location = astral.LocationInfo("City", "Country", "Europe/Berlin", 50.0, 8.0)
        >>> tz = zoneinfo.ZoneInfo("Europe/Berlin")
        >>> schedule = ScheduleEntry("daytime", "sunrise+00:00", "sunset-00:00",
        ...                          location=location, tz=tz)
    """

    def __init__(
        self,
        name: str,
        start: str,
        stop: str,
        location: astral.LocationInfo | None = None,
        tz: datetime.tzinfo | None = None,
        skip_days: int = 0,
        skip_offset: int = 0,
    ):
        if not tz:
            tz = local_tz()

        # schedule attributes
        self.name = name
        self._start = start
        self._stop = stop
        self._tz = tz
        self._location = location
        self._skip_days = skip_days
        self._skip_offset = skip_offset

    def prev_start(self, now: datetime.datetime | None = None) -> datetime.datetime:
        """Get the timestamp of the schedule's most recent start time.

        Returns the most recent start time that occurred at or before the given
        time (or current time if not specified). Takes skip_days into account.

        Args:
            now: Reference datetime. Defaults to current time if not provided.

        Returns:
            datetime.datetime: The timestamp of the previous schedule start.

        Example:
            >>> import datetime
            >>> schedule = ScheduleEntry("daily", "09:00", "17:00", tz=datetime.UTC)
            >>> now = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=datetime.UTC)
            >>> schedule.prev_start(now)
            datetime.datetime(2025, 2, 17, 9, 0, tzinfo=datetime.timezone.utc)
        """
        return self.parse_timing(self._start, forward=False, now=now, skip_days=self._skip_days)

    def prev_stop(self, now: datetime.datetime | None = None) -> datetime.datetime:
        """Get the stop time of the most recent schedule run.

        Returns the stop time associated with the most recent start time. Note that
        this timestamp may be in the future if the schedule is currently active.

        Args:
            now: Reference datetime. Defaults to current time if not provided.

        Returns:
            datetime.datetime: The timestamp of the previous schedule's stop time.
                May be in the future if the schedule is still running.

        Example:
            >>> import datetime
            >>> schedule = ScheduleEntry("daily", "09:00", "17:00", tz=datetime.UTC)
            >>> now = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=datetime.UTC)
            >>> schedule.prev_stop(now)
            datetime.datetime(2025, 2, 17, 17, 0, tzinfo=datetime.timezone.utc)
        """
        now = now or datetime.datetime.now(tz=self._tz)

        # get previous start and it's stop
        prev_start = self.prev_start(now)
        prev_start_stop = self.parse_timing(self._stop, now=prev_start)

        return prev_start_stop

    def next_start(self, now: datetime.datetime | None = None) -> datetime.datetime:
        """Get the timestamp of the schedule's next start time.

        Returns the next start time that will occur after the given time (or
        current time if not specified). Takes skip_days into account.

        Args:
            now: Reference datetime. Defaults to current time if not provided.

        Returns:
            datetime.datetime: The timestamp of the next schedule start.

        Example:
            >>> import datetime
            >>> schedule = ScheduleEntry("daily", "09:00", "17:00", tz=datetime.UTC)
            >>> now = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=datetime.UTC)
            >>> schedule.next_start(now)
            datetime.datetime(2025, 2, 18, 9, 0, tzinfo=datetime.timezone.utc)
        """
        return self.parse_timing(self._start, now=now, skip_days=self._skip_days)

    def next_stop(self, now: datetime.datetime | None = None) -> datetime.datetime:
        """Get the stop time of the schedule's next run.

        Returns the stop time associated with the next start time.

        Args:
            now: Reference datetime. Defaults to current time if not provided.

        Returns:
            datetime.datetime: The timestamp of the next schedule's stop time.

        Example:
            >>> import datetime
            >>> schedule = ScheduleEntry("daily", "09:00", "17:00", tz=datetime.UTC)
            >>> now = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=datetime.UTC)
            >>> schedule.next_stop(now)
            datetime.datetime(2025, 2, 18, 17, 0, tzinfo=datetime.timezone.utc)
        """
        now = now or datetime.datetime.now(tz=self._tz)

        next_start: datetime.datetime = self.next_start(now)
        next_start_stop = self.parse_timing(self._stop, now=next_start)

        return next_start_stop

    def active(self, now: datetime.datetime | None = None) -> bool:
        """Check if the schedule is currently active.

        A schedule is considered active if the stop time of the most recent run
        is in the future (meaning the schedule hasn't ended yet).

        Args:
            now: Reference datetime. Defaults to current time if not provided.

        Returns:
            bool: True if the schedule is currently active, False otherwise.

        Example:
            >>> import datetime
            >>> schedule = ScheduleEntry("daily", "09:00", "17:00", tz=datetime.UTC)
            >>> now = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=datetime.UTC)
            >>> schedule.active(now)  # 3 PM is between 9 AM and 5 PM
            True
            >>> late = datetime.datetime(2025, 2, 17, 20, 0, 0, tzinfo=datetime.UTC)
            >>> schedule.active(late)  # 8 PM is after 5 PM
            False
        """
        now = now or datetime.datetime.now(tz=self._tz)

        # active if stop of previous run's stop is in the future
        return self.prev_stop(now) > now

    def parse_timing(
        self,
        time_str: str,
        day: int = 0,
        forward: bool = True,
        now: datetime.datetime | None = None,
        skip_days: int = 0,
    ) -> datetime.datetime:
        """Parse a time string and return a datetime object.

        This internal method handles the parsing of time strings, supporting both
        absolute times and sunrise/sunset-based relative times. It recursively
        searches forward or backward to find the appropriate timestamp.

        Args:
            time_str: Time string to parse. Can be:
                - Absolute time: "HH:MM" or seconds since midnight
                - Sunrise-based: "sunrise", "sunrise+30m", "sunrise-1h"
                - Sunset-based: "sunset", "sunset+30m", "sunset-1h"
            day: Day offset from the reference date (0 = reference date).
            forward: If True, search forward in time. If False, search backward.
            now: Reference datetime. Defaults to current time if not provided.
            skip_days: Number of days to skip between valid schedule dates.

        Returns:
            datetime.datetime: The parsed timestamp.

        Note:
            This is an internal method primarily used by prev_start(), next_start(),
            prev_stop(), and next_stop(). Direct usage is typically not necessary.
        """
        # take the calendar day in the schedule's timezone, not in now's
        now = (now or datetime.datetime.now()).astimezone(self._tz)
        date = now.date() + datetime.timedelta(days=day)

        ref, op, dur = time_str.partition("+") if "+" in time_str else time_str.partition("-")
        if op or ref in SUN_EVENTS:
            # sun event with optional offset, e.g. "sunrise", "sunset-1h"
            assert self._location
            ref_ts = astral.sun.sun(self._location.observer, date=date, tzinfo=self._tz)[ref]
            offset_s = pytimeparse.parse(dur, granularity="minutes") or 0.0
            offset = datetime.timedelta(seconds=offset_s)
            ts = ref_ts - offset if op == "-" else ref_ts + offset
        else:
            # assume absolute time
            offset_s = pytimeparse.parse(time_str, granularity="minutes") or 0.0
            offset = datetime.timedelta(seconds=offset_s)
            ref_ts = datetime.datetime.combine(date, datetime.time(0, 0, 0), tzinfo=self._tz)
            ts = ref_ts + offset

        # evaluate parsed timestamp
        days_mod = (date.timetuple().tm_yday - self._skip_offset) % (skip_days + 1)
        if forward:
            if days_mod:
                # if this is not a day to be executed on, recurse with day+1
                return self.parse_timing(time_str, day + 1, forward=forward, now=now, skip_days=skip_days)
            elif ts < now:
                # if timestamp is in the past or now, recurse with day+1
                return self.parse_timing(time_str, day + 1, forward=forward, now=now, skip_days=skip_days)
            else:
                # return timestamp of the future
                return ts
        else:
            if days_mod:
                # if this is not a day to be executed on, recurse with day-1
                return self.parse_timing(time_str, day - 1, forward=forward, now=now, skip_days=skip_days)
            elif ts > now:
                # if timestamp is in the future, recurse with day-1
                return self.parse_timing(time_str, day - 1, forward=forward, now=now, skip_days=skip_days)
            else:
                # return timestamp of the past
                return ts

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r}, start={self._start!r}, stop={self._stop!r})"
