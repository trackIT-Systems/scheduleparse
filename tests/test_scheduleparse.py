import datetime
import logging
import os
import zoneinfo

import astral
import astral.sun
import pytest

from scheduleparse import ScheduleEntry, local_tz

BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")
BERLIN_LOC = astral.LocationInfo("Berlin", "Germany", "Europe/Berlin", 52.52, 13.405)


@pytest.fixture(autouse=True)
def utc_system_tz(monkeypatch):
    """Make the default timezone independent of the host running the tests."""
    monkeypatch.setenv("TZ", "UTC")


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


# Edge Cases & Error Handling Tests


def test_invalid_time_format_high_hour():
    """Test that invalid hour values (>24) still parse but may give unexpected results."""
    # pytimeparse will parse "25:00" as 25 hours = 90000 seconds
    se = ScheduleEntry("invalid-hour", "25:00", "26:00", tz=datetime.UTC)
    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    # Should create a schedule starting at 01:00 next day (25 hours from midnight)
    next_start = se.next_start(now)
    assert next_start.hour == 1  # 25 hours = 1 day + 1 hour


def test_invalid_time_format_high_minute():
    """Test that invalid minute values are handled by pytimeparse."""
    # pytimeparse will parse "12:99" as 12 hours + 99 minutes = 13:39
    se = ScheduleEntry("invalid-minute", "12:99", "13:00", tz=datetime.UTC)
    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    next_start = se.next_start(now)
    assert next_start.hour == 13
    assert next_start.minute == 39


def test_missing_location_for_sunrise():
    """Test that sunrise/sunset without location raises AssertionError."""
    se = ScheduleEntry("no-location", "sunrise+00:00", "sunset-00:00", tz=datetime.UTC)
    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    with pytest.raises(AssertionError):
        se.active(now)


def test_midnight_boundary_conditions():
    """Test schedules at exactly midnight."""
    # Schedule starting at midnight
    se = ScheduleEntry("midnight-start", "00:00", "01:00", tz=datetime.UTC)
    midnight = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=datetime.UTC)
    assert se.active(midnight)
    assert se.prev_start(midnight) == midnight
    assert se.next_start(midnight) == midnight


def test_large_skip_days():
    """Test schedule with very large skip_days value."""
    se = ScheduleEntry("weekly", "12:00", "13:00", skip_days=6, tz=datetime.UTC)
    now = datetime.datetime(2025, 2, 17, 12, 30, 0, tzinfo=datetime.UTC)

    # 2025-02-17 is day 48 of the year, 48 % 7 == 6, so the next run is on day 49
    assert not se.active(now)
    assert se.next_start(now) == datetime.datetime(2025, 2, 18, 12, 0, 0, tzinfo=datetime.UTC)
    assert se.next_start(se.next_stop(now)) == datetime.datetime(2025, 2, 25, 12, 0, 0, tzinfo=datetime.UTC)
    assert se.prev_start(now) == datetime.datetime(2025, 2, 11, 12, 0, 0, tzinfo=datetime.UTC)


def test_negative_skip_days():
    """Test that negative skip_days raises ZeroDivisionError."""
    # Negative skip_days is not supported and should cause an error
    se = ScheduleEntry("negative-skip", "12:00", "13:00", skip_days=-1, tz=datetime.UTC)
    now = datetime.datetime(2025, 2, 17, 12, 30, 0, tzinfo=datetime.UTC)

    with pytest.raises(ZeroDivisionError):
        se.next_start(now)


# Comprehensive Feature Coverage Tests


def test_overnight_with_skip_days():
    """Test overnight schedule combined with skip_days."""
    se = ScheduleEntry("overnight-bidaily", "20:00", "05:00", skip_days=1, tz=datetime.UTC)

    # 2025-02-17 is day 48 (even), so the run starts that evening
    night = datetime.datetime(2025, 2, 17, 23, 0, 0, tzinfo=datetime.UTC)
    assert se.active(night)
    assert se.prev_start(night) == datetime.datetime(2025, 2, 17, 20, 0, 0, tzinfo=datetime.UTC)
    assert se.prev_stop(night) == datetime.datetime(2025, 2, 18, 5, 0, 0, tzinfo=datetime.UTC)
    assert se.next_start(night) == datetime.datetime(2025, 2, 19, 20, 0, 0, tzinfo=datetime.UTC)

    # the following night is skipped
    assert not se.active(datetime.datetime(2025, 2, 18, 23, 0, 0, tzinfo=datetime.UTC))


def test_multiple_timezones():
    """Test schedule behavior across different timezones."""
    tz_berlin = zoneinfo.ZoneInfo("Europe/Berlin")
    tz_ny = zoneinfo.ZoneInfo("America/New_York")

    # Create schedule in Berlin timezone
    se = ScheduleEntry("berlin-schedule", "12:00", "13:00", tz=tz_berlin)

    # Check with Berlin time
    berlin_noon = datetime.datetime(2025, 6, 17, 12, 30, 0, tzinfo=tz_berlin)
    assert se.active(berlin_noon)

    # Berlin noon in June is 6 AM in NY, passed without converting
    ny_morning = datetime.datetime(2025, 6, 17, 6, 30, 0, tzinfo=tz_ny)
    assert se.active(ny_morning)
    assert se.prev_start(ny_morning) == datetime.datetime(2025, 6, 17, 12, 0, 0, tzinfo=tz_berlin)

    # 21:00 in NY is already the next day in Berlin
    ny_evening = datetime.datetime(2025, 6, 17, 21, 0, 0, tzinfo=tz_ny)
    assert not se.active(ny_evening)
    assert se.next_start(ny_evening) == datetime.datetime(2025, 6, 18, 12, 0, 0, tzinfo=tz_berlin)


def test_sunrise_negative_offset():
    """Test sunrise with negative offset (before sunrise)."""
    tzname = "Europe/Berlin"
    tzinfo = zoneinfo.ZoneInfo(tzname)
    location = astral.LocationInfo("Berlin", "Germany", tzname, 52.52, 13.405)

    # 30 minutes before sunrise to 30 minutes after sunrise
    se = ScheduleEntry("pre-sunrise", "sunrise-30m", "sunrise+30m", location=location, tz=tzinfo)

    # Calculate expected sunrise time
    test_date = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=tzinfo)
    sun_times = astral.sun.sun(location.observer, date=test_date.date(), tzinfo=tzinfo)
    sunrise = sun_times["sunrise"]

    # Test 15 minutes before sunrise (should be active)
    before_sunrise = sunrise - datetime.timedelta(minutes=15)
    assert se.active(before_sunrise)

    # Test 45 minutes before sunrise (should be inactive)
    way_before_sunrise = sunrise - datetime.timedelta(minutes=45)
    assert not se.active(way_before_sunrise)


def test_sunset_positive_offset():
    """Test sunset with positive offset (after sunset)."""
    tzname = "Europe/Berlin"
    tzinfo = zoneinfo.ZoneInfo(tzname)
    location = astral.LocationInfo("Berlin", "Germany", tzname, 52.52, 13.405)

    # Sunset to 1 hour after sunset
    se = ScheduleEntry("post-sunset", "sunset+00:00", "sunset+1h", location=location, tz=tzinfo)

    # Calculate expected sunset time
    test_date = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=tzinfo)
    sun_times = astral.sun.sun(location.observer, date=test_date.date(), tzinfo=tzinfo)
    sunset = sun_times["sunset"]

    # Test 30 minutes after sunset (should be active)
    after_sunset = sunset + datetime.timedelta(minutes=30)
    assert se.active(after_sunset)

    # Test 90 minutes after sunset (should be inactive)
    way_after_sunset = sunset + datetime.timedelta(minutes=90)
    assert not se.active(way_after_sunset)


def test_identical_start_stop_times():
    """Test schedule with same start and stop time."""
    se = ScheduleEntry("instant", "12:00", "12:00", tz=datetime.UTC)

    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    # Should not be active as stop == start
    assert not se.active(now)

    before = datetime.datetime(2025, 2, 17, 11, 59, 0, tzinfo=datetime.UTC)
    assert not se.active(before)


def test_prev_next_at_exact_start():
    """Test prev/next calculations at exact start time."""
    se = ScheduleEntry("exact-start", "12:00", "13:00", tz=datetime.UTC)

    # At exactly start time
    exact_start = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)

    # prev_start and next_start should both return the current time
    assert se.prev_start(exact_start) == exact_start
    assert se.next_start(exact_start) == exact_start

    # Should be active at start time
    assert se.active(exact_start)


def test_prev_next_at_exact_stop():
    """Test prev/next calculations at exact stop time."""
    se = ScheduleEntry("exact-stop", "12:00", "13:00", tz=datetime.UTC)

    # At exactly stop time
    exact_stop = datetime.datetime(2025, 2, 17, 13, 0, 0, tzinfo=datetime.UTC)

    # Should NOT be active at exact stop time (stop is exclusive)
    assert not se.active(exact_stop)

    # prev_start should be today at 12:00
    assert se.prev_start(exact_stop) == datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)

    # next_start should be tomorrow at 12:00
    assert se.next_start(exact_stop) == datetime.datetime(2025, 2, 18, 12, 0, 0, tzinfo=datetime.UTC)


def test_long_running_schedule():
    """Test schedule that runs for extended hours beyond standard day."""
    # Schedule from midnight to 6 AM (which wraps to next day like overnight schedule)
    se = ScheduleEntry("long-run", "00:00", "06:00", tz=datetime.UTC)

    # Monday at 3 AM - should be active
    monday_3am = datetime.datetime(2025, 2, 17, 3, 0, 0, tzinfo=datetime.UTC)
    assert se.active(monday_3am)

    # Monday at noon - should NOT be active
    monday_noon = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    assert not se.active(monday_noon)

    # Verify prev_stop is at 6 AM
    prev_stop = se.prev_stop(monday_noon)
    assert prev_stop.hour == 6


def test_edge_time_23_59():
    """Test schedule ending at 23:59."""
    se = ScheduleEntry("almost-midnight", "00:00", "23:59", tz=datetime.UTC)

    # Should be active almost all day
    noon = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
    assert se.active(noon)

    # Should be active at 23:58
    late = datetime.datetime(2025, 2, 17, 23, 58, 0, tzinfo=datetime.UTC)
    assert se.active(late)

    # Should NOT be active at 23:59 (stop time is exclusive)
    exact_end = datetime.datetime(2025, 2, 17, 23, 59, 0, tzinfo=datetime.UTC)
    assert not se.active(exact_end)


def test_edge_time_00_01():
    """Test schedule with very short duration after midnight."""
    se = ScheduleEntry("one-minute", "00:00", "00:01", tz=datetime.UTC)

    # Should be active at midnight
    midnight = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=datetime.UTC)
    assert se.active(midnight)

    # Should be active at 00:00:30
    thirty_sec = datetime.datetime(2025, 2, 17, 0, 0, 30, tzinfo=datetime.UTC)
    assert se.active(thirty_sec)

    # Should NOT be active at 00:01
    one_min = datetime.datetime(2025, 2, 17, 0, 1, 0, tzinfo=datetime.UTC)
    assert not se.active(one_min)


def test_skip_days_with_different_offsets():
    """Test multiple schedules with same skip_days but different offsets don't overlap."""
    se0 = ScheduleEntry("shift-a", "08:00", "16:00", skip_days=2, skip_offset=0, tz=datetime.UTC)
    se1 = ScheduleEntry("shift-b", "08:00", "16:00", skip_days=2, skip_offset=1, tz=datetime.UTC)
    se2 = ScheduleEntry("shift-c", "08:00", "16:00", skip_days=2, skip_offset=2, tz=datetime.UTC)

    # Test over multiple days to ensure they rotate
    day1 = datetime.datetime(2025, 2, 17, 10, 0, 0, tzinfo=datetime.UTC)
    day2 = datetime.datetime(2025, 2, 18, 10, 0, 0, tzinfo=datetime.UTC)
    day3 = datetime.datetime(2025, 2, 19, 10, 0, 0, tzinfo=datetime.UTC)
    day4 = datetime.datetime(2025, 2, 20, 10, 0, 0, tzinfo=datetime.UTC)

    # Check that on each day, only one schedule is active
    for day in [day1, day2, day3, day4]:
        active_count = sum([se0.active(day), se1.active(day), se2.active(day)])
        assert active_count == 1, f"Expected exactly 1 active schedule on {day}, got {active_count}"


def test_timezone_aware_vs_naive():
    """Test that timezone-aware datetimes work correctly."""
    tz = zoneinfo.ZoneInfo("Europe/Berlin")
    se = ScheduleEntry("tz-aware", "12:00", "13:00", tz=tz)

    # Timezone-aware datetime
    aware_dt = datetime.datetime(2025, 2, 17, 12, 30, 0, tzinfo=tz)
    assert se.active(aware_dt)

    # A naive datetime is interpreted as system local time (UTC via the fixture)
    naive_dt = datetime.datetime(2025, 2, 17, 11, 30, 0)
    assert se.prev_start(naive_dt) == datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=tz)
    assert se.next_start(naive_dt) == datetime.datetime(2025, 2, 18, 12, 0, 0, tzinfo=tz)


def test_prev_stop_during_active_schedule():
    """Test that prev_stop returns future time when schedule is currently active."""
    se = ScheduleEntry("active-now", "12:00", "18:00", tz=datetime.UTC)

    # Check during active period
    during = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=datetime.UTC)
    assert se.active(during)

    prev_stop = se.prev_stop(during)
    # prev_stop should be in the future (18:00 today)
    assert prev_stop > during
    assert prev_stop == datetime.datetime(2025, 2, 17, 18, 0, 0, tzinfo=datetime.UTC)


def test_next_stop_after_schedule():
    """Test that next_stop returns correct time after schedule has ended."""
    se = ScheduleEntry("ended", "12:00", "18:00", tz=datetime.UTC)

    # Check after schedule has ended
    after = datetime.datetime(2025, 2, 17, 20, 0, 0, tzinfo=datetime.UTC)
    assert not se.active(after)

    next_stop = se.next_stop(after)
    # next_stop should be tomorrow at 18:00
    assert next_stop == datetime.datetime(2025, 2, 18, 18, 0, 0, tzinfo=datetime.UTC)


def test_overnight_relative_time_berlin_15min_intervals():
    """Test overnight schedule with relative times in Berlin timezone, checking every 15 minutes."""
    tzname = "Europe/Berlin"
    tzinfo = zoneinfo.ZoneInfo(tzname)
    location = astral.LocationInfo("Berlin", "Germany", tzname, 52.52, 13.405)

    # Schedule from 1 hour after sunset until 30 minutes after sunrise (overnight)
    se = ScheduleEntry("overnight-relative", "sunset+1h", "sunrise+30m", location=location, tz=tzinfo)

    def sun(date):
        return astral.sun.sun(location.observer, date=date, tzinfo=tzinfo)

    day = datetime.date(2025, 2, 17)
    windows = [
        (sun(d)["sunset"] + datetime.timedelta(hours=1), sun(d + datetime.timedelta(days=1))["sunrise"] + datetime.timedelta(minutes=30))
        for d in (day - datetime.timedelta(days=1), day)
    ]

    # every 15 minutes over 24 hours, compare with the expected windows
    current = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=tzinfo)
    states = []
    while current < datetime.datetime(2025, 2, 18, 0, 0, 0, tzinfo=tzinfo):
        expected = any(start <= current < stop for start, stop in windows)
        assert se.active(current) == expected, f"wrong state at {current}"
        states.append(expected)
        current += datetime.timedelta(minutes=15)

    # active in the morning, inactive during the day, active again in the evening
    transitions = sum(a != b for a, b in zip(states, states[1:]))
    assert transitions == 2

    # stop of the evening run is the next morning
    evening = windows[1][0] + datetime.timedelta(minutes=15)
    assert se.prev_start(evening) == windows[1][0]
    assert se.prev_stop(evening) == windows[1][1]


def test_now_in_other_timezone():
    """The calendar day comes from the schedule's timezone, not from `now`'s.

    00:30 in Berlin is 23:30 UTC on the previous day (trackIT-Systems/wittypi4#9).
    """
    tz = zoneinfo.ZoneInfo("Europe/Berlin")
    se = ScheduleEntry("after_midnight", "00:01", "01:00", tz=tz)
    now = datetime.datetime(2025, 12, 9, 0, 30, tzinfo=tz)

    for n in (now, now.astimezone(datetime.UTC)):
        assert se.active(n)
        assert se.prev_start(n) == datetime.datetime(2025, 12, 9, 0, 1, tzinfo=tz)
        assert se.prev_stop(n) == datetime.datetime(2025, 12, 9, 1, 0, tzinfo=tz)
        assert se.next_start(n) == datetime.datetime(2025, 12, 10, 0, 1, tzinfo=tz)


def test_default_timezone_follows_dst(monkeypatch):
    """Without an explicit tz the system zone is used, including its DST rules."""
    monkeypatch.setenv("TZ", "Europe/Berlin")
    tz = zoneinfo.ZoneInfo("Europe/Berlin")
    se = ScheduleEntry("evening", "22:00", "23:00")

    for month in (7, 12):
        now = datetime.datetime(2025, month, 1, 12, 0, tzinfo=datetime.UTC)
        assert se.next_start(now) == datetime.datetime(2025, month, 1, 22, 0, tzinfo=tz)


# local_tz()


def test_local_tz_from_env_strips_colon(monkeypatch):
    monkeypatch.setenv("TZ", ":Europe/Berlin")
    assert local_tz() == BERLIN


@pytest.mark.skipif(not os.path.exists("/etc/localtime"), reason="no /etc/localtime")
def test_local_tz_from_etc_localtime(monkeypatch):
    monkeypatch.delenv("TZ")
    tz = local_tz()
    assert isinstance(tz, zoneinfo.ZoneInfo)
    assert str(tz) == "localtime"


@pytest.mark.parametrize("key", ["Not/AZone", "../etc/passwd"])
def test_local_tz_fallback(monkeypatch, caplog, key):
    monkeypatch.setenv("TZ", key)
    with caplog.at_level(logging.WARNING, logger="scheduleparse"):
        tz = local_tz()
    assert isinstance(tz, datetime.timezone)
    assert "Couldn't determine system timezone" in caplog.text


# Time string formats


@pytest.mark.parametrize(
    "time_str, expected",
    [
        ("09:30", datetime.time(9, 30)),
        ("9h30m", datetime.time(9, 30)),
        ("12:00:30", datetime.time(12, 0, 30)),
        ("90m", datetime.time(1, 30)),
    ],
)
def test_absolute_formats(time_str, expected):
    se = ScheduleEntry("fmt", time_str, "23:59", tz=datetime.UTC)
    now = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=datetime.UTC)
    assert se.next_start(now) == datetime.datetime.combine(now.date(), expected, tzinfo=datetime.UTC)


@pytest.mark.parametrize("event", ["dawn", "sunrise", "noon", "sunset", "dusk"])
@pytest.mark.parametrize(
    "offset_str, offset",
    [
        ("+0m", datetime.timedelta(0)),
        ("+1h30m", datetime.timedelta(hours=1, minutes=30)),
        ("+01:30", datetime.timedelta(hours=1, minutes=30)),
        ("-90m", -datetime.timedelta(minutes=90)),
        ("-1h", -datetime.timedelta(hours=1)),
    ],
)
def test_sun_events_with_offsets(event, offset_str, offset):
    se = ScheduleEntry("sun", event + offset_str, "23:59", location=BERLIN_LOC, tz=BERLIN)
    date = datetime.date(2025, 2, 17)
    expected = astral.sun.sun(BERLIN_LOC.observer, date=date, tzinfo=BERLIN)[event] + offset
    now = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=BERLIN)
    assert se.next_start(now) == expected


def test_unknown_sun_event():
    se = ScheduleEntry("moon", "moonrise+1h", "23:59", location=BERLIN_LOC, tz=BERLIN)
    with pytest.raises(KeyError):
        se.next_start(datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=BERLIN))


def test_polar_day_raises():
    """Astral can't compute sunrise/sunset when the sun never sets; behavior is undefined so far."""
    tz = zoneinfo.ZoneInfo("Europe/Oslo")
    tromso = astral.LocationInfo("Tromso", "Norway", "Europe/Oslo", 69.65, 18.96)
    se = ScheduleEntry("midnight-sun", "sunrise+0m", "sunset-0m", location=tromso, tz=tz)
    with pytest.raises(ValueError):
        se.active(datetime.datetime(2025, 6, 21, 12, 0, 0, tzinfo=tz))


# Results and invariants


@pytest.mark.parametrize("now_tz", [datetime.UTC, BERLIN, zoneinfo.ZoneInfo("America/New_York")])
def test_results_in_schedule_timezone(now_tz):
    se = ScheduleEntry("tz", "12:00", "13:00", tz=BERLIN)
    now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=now_tz)
    for ts in (se.prev_start(now), se.prev_stop(now), se.next_start(now), se.next_stop(now)):
        assert ts.tzinfo is BERLIN


SCHEDULES = [
    ScheduleEntry("day", "09:00", "17:00", tz=BERLIN),
    ScheduleEntry("night", "22:00", "06:00", tz=BERLIN),
    ScheduleEntry("bidaily", "08:00", "16:00", skip_days=1, tz=BERLIN),
    ScheduleEntry("sun", "sunrise-30m", "sunset+30m", location=BERLIN_LOC, tz=BERLIN),
    ScheduleEntry("sun-night", "sunset+1h", "sunrise+30m", location=BERLIN_LOC, tz=BERLIN),
    ScheduleEntry("sun-skip", "sunrise+0m", "noon+0m", skip_days=2, skip_offset=1, location=BERLIN_LOC, tz=BERLIN),
]


@pytest.mark.parametrize("se", SCHEDULES, ids=lambda se: se.name)
def test_invariants(se):
    """prev/next/active agree with each other at many points in time, including DST changes."""
    starts = [
        datetime.datetime(2025, 2, 17, tzinfo=datetime.UTC),
        datetime.datetime(2025, 3, 29, tzinfo=datetime.UTC),
        datetime.datetime(2025, 10, 25, tzinfo=datetime.UTC),
    ]
    for start in starts:
        for minutes in range(0, 3 * 24 * 60, 37):
            now = start + datetime.timedelta(minutes=minutes)
            prev_start, prev_stop = se.prev_start(now), se.prev_stop(now)
            next_start, next_stop = se.next_start(now), se.next_stop(now)

            assert prev_start <= now <= next_start
            assert prev_start <= prev_stop
            assert next_start <= next_stop
            assert se.active(now) == (prev_stop > now)
            # starting at prev_start gives prev_start, so both directions agree
            assert se.next_start(prev_start) == prev_start


def test_skip_days_with_sun_times():
    se = ScheduleEntry("sun-bidaily", "sunrise+0m", "sunset+0m", skip_days=1, location=BERLIN_LOC, tz=BERLIN)

    def sun(date):
        return astral.sun.sun(BERLIN_LOC.observer, date=date, tzinfo=BERLIN)

    # 2025-02-17 is day 48 (even), runs; 2025-02-18 is skipped
    noon_17 = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=BERLIN)
    noon_18 = datetime.datetime(2025, 2, 18, 12, 0, 0, tzinfo=BERLIN)
    assert se.active(noon_17)
    assert not se.active(noon_18)
    assert se.prev_start(noon_17) == sun(datetime.date(2025, 2, 17))["sunrise"]
    assert se.prev_stop(noon_17) == sun(datetime.date(2025, 2, 17))["sunset"]
    assert se.next_start(noon_17) == sun(datetime.date(2025, 2, 19))["sunrise"]


def test_sun_start_past_midnight():
    """In June in Berlin, sunset+3h is after midnight and belongs to the next calendar day."""
    se = ScheduleEntry("late", "sunset+3h", "sunrise+0m", location=BERLIN_LOC, tz=BERLIN)
    june_21 = astral.sun.sun(BERLIN_LOC.observer, date=datetime.date(2025, 6, 21), tzinfo=BERLIN)
    june_22 = astral.sun.sun(BERLIN_LOC.observer, date=datetime.date(2025, 6, 22), tzinfo=BERLIN)
    start = june_21["sunset"] + datetime.timedelta(hours=3)
    assert start.date() == datetime.date(2025, 6, 22)

    now = start + datetime.timedelta(minutes=10)
    assert se.active(now)
    assert se.prev_start(now) == start
    # the stop is computed from the start's calendar day
    assert se.prev_stop(now) == june_22["sunrise"]


# Daylight saving time (pinning current behavior)


def test_dst_spring_forward():
    # 2025-03-30: 02:00 CET jumps to 03:00 CEST, the day has 23 hours
    se = ScheduleEntry("allday", "00:00", "24:00", tz=BERLIN)
    noon = datetime.datetime(2025, 3, 30, 12, 0, 0, tzinfo=BERLIN)
    assert se.prev_start(noon) == datetime.datetime(2025, 3, 30, 0, 0, 0, tzinfo=BERLIN)
    assert se.prev_stop(noon) == datetime.datetime(2025, 3, 31, 0, 0, 0, tzinfo=BERLIN)
    assert se.prev_stop(noon).astimezone(datetime.UTC) - se.prev_start(noon).astimezone(datetime.UTC) == datetime.timedelta(hours=23)

    # times are wall-clock times: 01:00-04:00 lasts 2 real hours on this day
    se = ScheduleEntry("night", "01:00", "04:00", tz=BERLIN)
    assert se.active(datetime.datetime(2025, 3, 30, 3, 30, 0, tzinfo=BERLIN))
    assert not se.active(datetime.datetime(2025, 3, 30, 4, 0, 0, tzinfo=BERLIN))

    # 02:30 doesn't exist on this day, it is returned as the non-existent wall time with the old offset
    se = ScheduleEntry("gap", "02:30", "04:00", tz=BERLIN)
    start = se.next_start(datetime.datetime(2025, 3, 30, 0, 0, 0, tzinfo=BERLIN))
    assert (start.hour, start.minute) == (2, 30)
    assert start.utcoffset() == datetime.timedelta(hours=1)


def test_dst_fall_back():
    # 2025-10-26: 03:00 CEST goes back to 02:00 CET, 02:00-03:00 happens twice
    se = ScheduleEntry("twice", "02:00", "02:45", tz=BERLIN)
    first = datetime.datetime(2025, 10, 26, 0, 30, 0, tzinfo=datetime.UTC)  # 02:30 CEST
    second = datetime.datetime(2025, 10, 26, 1, 30, 0, tzinfo=datetime.UTC)  # 02:30 CET
    assert se.active(first)
    assert not se.active(second)
    # compare in UTC: comparing ambiguous times across zones is always unequal (PEP 495)
    assert se.prev_stop(second).astimezone(datetime.UTC) == datetime.datetime(2025, 10, 26, 0, 45, 0, tzinfo=datetime.UTC)

    se = ScheduleEntry("allday", "00:00", "24:00", tz=BERLIN)
    noon = datetime.datetime(2025, 10, 26, 12, 0, 0, tzinfo=BERLIN)
    assert se.prev_stop(noon).astimezone(datetime.UTC) - se.prev_start(noon).astimezone(datetime.UTC) == datetime.timedelta(hours=25)


# Known bugs: these tests describe the desired behavior and fail until it is fixed


@pytest.mark.xfail(strict=True, reason="skip_days uses the day of the year, which restarts at 1 on Jan 1")
def test_skip_days_across_new_year():
    se = ScheduleEntry("bidaily", "00:00", "24:00", skip_days=1, tz=datetime.UTC)
    now = datetime.datetime(2025, 12, 29, 12, 0, 0, tzinfo=datetime.UTC)
    starts = []
    for _ in range(3):
        now = se.next_start(now)
        starts.append(now.date())
        now += datetime.timedelta(hours=1)
    assert starts == [datetime.date(2025, 12, 30), datetime.date(2026, 1, 1), datetime.date(2026, 1, 3)]


@pytest.mark.xfail(strict=True, raises=TypeError, reason="active() compares the aware stop time with a naive now")
def test_active_with_naive_now():
    se = ScheduleEntry("naive", "12:00", "13:00", tz=datetime.UTC)
    assert se.active(datetime.datetime(2025, 2, 17, 12, 30, 0))


@pytest.mark.xfail(strict=True, reason="unparseable time strings silently resolve to midnight")
@pytest.mark.parametrize("time_str", ["garbage", "sunrise", "1:30 pm", "3600"])
def test_unparseable_time_raises(time_str):
    se = ScheduleEntry("bad", time_str, "23:00", location=BERLIN_LOC, tz=datetime.UTC)
    with pytest.raises(ValueError):
        se.next_start(datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC))


@pytest.mark.xfail(strict=True, raises=RecursionError, reason="each skipped day is a recursion level")
def test_large_skip_days_no_recursion_error():
    se = ScheduleEntry("rare", "12:00", "13:00", skip_days=2000, tz=datetime.UTC)
    se.next_start(datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC))


@pytest.mark.xfail(strict=True, reason="negative skip_days isn't validated, -2 runs daily")
def test_negative_skip_days_rejected():
    with pytest.raises(ValueError):
        ScheduleEntry("negative", "12:00", "13:00", skip_days=-2, tz=datetime.UTC)
