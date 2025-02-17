import datetime
import sys
import zoneinfo

import astral

from scheduleparse import ScheduleEntry


def test_on():
    se = ScheduleEntry("on", "00:00", "24:00")
    assert se.active()


def test_off():
    se = ScheduleEntry("off", "00:00", "00:00")
    assert not se.active()


def test_fixed():
    now = datetime.datetime(2025, 2, 17, 12, 00, 00, tzinfo=datetime.UTC)
    se = ScheduleEntry("fixed", "12:00", "12:05", tz=now.tzinfo)
    assert se.active(now)

    # test prev and next are equal, if we hit the exact start ts
    assert se.prev_start(now) == now
    assert se.next_start(now) == now
    assert se.prev_stop(now) == now + datetime.timedelta(minutes=5)
    assert se.next_stop(now) == now + datetime.timedelta(minutes=5)


def test_over_night():
    now = datetime.datetime(2025, 2, 17, 3, 00, 00, tzinfo=datetime.UTC)
    day = datetime.datetime(2025, 2, 17, 9, 00, 00, tzinfo=datetime.UTC)
    se = ScheduleEntry("over_night", "20:00", "05:00", tz=now.tzinfo)
    assert se.active(now)
    assert not se.active(day)


def test_now():
    now = datetime.datetime.now().astimezone()
    start = (now - datetime.timedelta(minutes=5)).strftime("%H:%M")
    end = (now + datetime.timedelta(minutes=5)).strftime("%H:%M")
    se = ScheduleEntry("now", start, end, tz=now.tzinfo)
    assert se.active(now)


def test_tz():
    tz = zoneinfo.ZoneInfo("Europe/Berlin")
    now = datetime.datetime(2025, 2, 17, 12, 00, 00, tzinfo=tz)
    se = ScheduleEntry("tz", "12:00", "12:05", tz=tz)
    assert se.active(now)


def test_astral():
    tzname = "Europe/Berlin"
    tzinfo = zoneinfo.ZoneInfo(tzname)
    coelbe = astral.LocationInfo("Coelbe", "Germany", tzname, 50.85318, 8.78735)
    se = ScheduleEntry("daytime", "sunrise+00:00", "sunset-00:00", location=coelbe, tz=tzinfo)

    lunch = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=tzinfo)
    assert se.active(lunch)
    afterwork = datetime.datetime(2025, 2, 17, 18, 0, 0, tzinfo=tzinfo)
    assert not se.active(afterwork)
    morning_coffee = datetime.datetime(2025, 2, 17, 8, 0, 0, tzinfo=tzinfo)
    assert se.active(morning_coffee)

    sunrise = datetime.datetime.fromisoformat("2025-02-17 07:33:26.860012+01:00")
    sunset = datetime.datetime.fromisoformat("2025-02-17 17:44:59.100299+01:00")
    assert se.prev_start(lunch) == sunrise
    assert se.prev_stop(lunch) == sunset


def test_skip():
    se = ScheduleEntry("bidaily", "00:00", "24:00", skip_days=1, tz=datetime.UTC)

    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    assert se.active(now)
    assert se.prev_start(now) == datetime.datetime.fromisoformat("2025-02-17 00:00:00+00:00")
    assert se.prev_stop(now) == datetime.datetime.fromisoformat("2025-02-18 00:00:00+00:00")
    assert se.next_start(now) == datetime.datetime.fromisoformat("2025-02-19 00:00:00+00:00")
    assert se.next_stop(now) == datetime.datetime.fromisoformat("2025-02-20 00:00:00+00:00")

    tomorrow = datetime.datetime(2025, 2, 18, 12, 0, 0, tzinfo=datetime.UTC)
    assert not se.active(tomorrow)


def test_skip_offset():
    se = ScheduleEntry("bidaily", "00:00", "24:00", skip_days=1, skip_offset=1, tz=datetime.UTC)

    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    assert not se.active(now)
    assert se.prev_start(now) == datetime.datetime.fromisoformat("2025-02-16 00:00:00+00:00")
    assert se.prev_stop(now) == datetime.datetime.fromisoformat("2025-02-17 00:00:00+00:00")
    assert se.next_start(now) == datetime.datetime.fromisoformat("2025-02-18 00:00:00+00:00")
    assert se.next_stop(now) == datetime.datetime.fromisoformat("2025-02-19 00:00:00+00:00")

    tomorrow = datetime.datetime(2025, 2, 18, 12, 0, 0, tzinfo=datetime.UTC)
    assert se.active(tomorrow)


def test_skip_offset3():
    se0 = ScheduleEntry("fourdaily-0", "00:00", "24:00", skip_days=3, skip_offset=0, tz=datetime.UTC)
    se1 = ScheduleEntry("fourdaily-1", "00:00", "24:00", skip_days=3, skip_offset=1, tz=datetime.UTC)
    se2 = ScheduleEntry("fourdaily-2", "00:00", "24:00", skip_days=3, skip_offset=2, tz=datetime.UTC)
    se3 = ScheduleEntry("fourdaily-2", "00:00", "24:00", skip_days=3, skip_offset=3, tz=datetime.UTC)

    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    assert se0.active(now)
    assert not se1.active(now)
    assert not se2.active(now)
    assert not se3.active(now)

    assert se0.next_start(now) == datetime.datetime.fromisoformat("2025-02-21 00:00:00+00:00")
    assert se1.next_start(now) == datetime.datetime.fromisoformat("2025-02-18 00:00:00+00:00")
    assert se2.next_start(now) == datetime.datetime.fromisoformat("2025-02-19 00:00:00+00:00")
    assert se3.next_start(now) == datetime.datetime.fromisoformat("2025-02-20 00:00:00+00:00")


def test_repr():
    se = ScheduleEntry("bidaily", "00:00", "24:00")
    se_repr = str(se)
    se2 = eval(se_repr)

    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    assert se.next_start(now) == se2.next_start(now)
