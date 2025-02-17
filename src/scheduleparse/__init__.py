import datetime
import logging

import astral
import astral.sun
import pytimeparse

logger = logging.getLogger(__name__)


class ScheduleEntry:
    def __init__(
        self,
        name: str,
        start: str,
        stop: str,
        location: astral.LocationInfo | None = None,
        tz: datetime.tzinfo | None = None,
        skip_days: int = 0,
    ):
        # get local timezone
        if not tz:
            tz = datetime.datetime.now().astimezone().tzinfo

        # schedule attributes
        self.name = name
        self._start = start
        self._stop = stop
        self._tz = tz
        self._location = location
        self._skip_days = skip_days

    def prev_start(self, now: datetime.datetime | None = None) -> datetime.datetime:
        """returns the timestamp of the schedule's previous run's start"""
        return self.parse_timing(self._start, forward=False, now=now, skip_days=self._skip_days)

    def prev_stop(self, now: datetime.datetime | None = None) -> datetime.datetime:
        """returns the timestamp of the schedule's previous run's stop

        timestamp may be in the future, as the schedule may still be running
        """
        now = now or datetime.datetime.now(tz=self._tz)

        # get previous start and it's stop
        prev_start = self.prev_start(now)
        prev_start_stop = self.parse_timing(self._stop, now=prev_start)

        return prev_start_stop

    def next_start(self, now: datetime.datetime | None = None) -> datetime.datetime:
        """returns the timestamp of the schedule's next run's start"""
        return self.parse_timing(self._start, now=now, skip_days=self._skip_days)

    def next_stop(self, now: datetime.datetime | None = None) -> datetime.datetime:
        """returns the timestamp of the schedule's next run's stop"""
        now = now or datetime.datetime.now(tz=self._tz)

        next_start: datetime.datetime = self.next_start(now)
        next_start_stop = self.parse_timing(self._stop, now=next_start)

        return next_start_stop

    def active(self, now: datetime.datetime | None = None) -> bool:
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
        # initizalize now with datetime.now() if not set
        now = now or datetime.datetime.now(tz=self._tz)
        date = now.date() + datetime.timedelta(days=day)

        if "+" in time_str:
            assert self._location
            ref, op, dur = time_str.partition("+")
            ref_ts = astral.sun.sun(self._location.observer, date=date, tzinfo=self._tz)[ref]
            offset_s = pytimeparse.parse(dur, granularity="minutes") or 0.0
            offset = datetime.timedelta(seconds=offset_s)
            ts = ref_ts + offset
        elif "-" in time_str:
            assert self._location
            ref, op, dur = time_str.partition("-")
            ref_ts = astral.sun.sun(self._location.observer, date=date, tzinfo=self._tz)[ref]
            offset_s = pytimeparse.parse(dur, granularity="minutes") or 0.0
            offset = datetime.timedelta(seconds=offset_s)
            ts = ref_ts - offset
        else:
            # assume absolute time
            offset_s = pytimeparse.parse(time_str, granularity="minutes") or 0.0
            offset = datetime.timedelta(seconds=offset_s)
            ref_ts = datetime.datetime.combine(date, datetime.time(0, 0, 0), tzinfo=self._tz)
            ts = ref_ts + offset

        # evaluate parsed timestamp
        days_mod = date.timetuple().tm_yday % (skip_days + 1)
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
