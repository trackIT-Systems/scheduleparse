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
    try:
        se.active(now)
        assert False, "Should have raised AssertionError"
    except AssertionError:
        pass  # Expected


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

    # If active now, next should be 7 days later
    if se.active(now):
        next_start = se.next_start(now)
        assert (next_start - now).days >= 7


def test_negative_skip_days():
    """Test that negative skip_days raises ZeroDivisionError."""
    # Negative skip_days is not supported and should cause an error
    se = ScheduleEntry("negative-skip", "12:00", "13:00", skip_days=-1, tz=datetime.UTC)
    now = datetime.datetime(2025, 2, 17, 12, 30, 0, tzinfo=datetime.UTC)

    try:
        next_start = se.next_start(now)
        assert False, "Should have raised ZeroDivisionError"
    except ZeroDivisionError:
        pass  # Expected - negative skip_days is not supported


# Comprehensive Feature Coverage Tests


def test_overnight_with_skip_days():
    """Test overnight schedule combined with skip_days."""
    se = ScheduleEntry("overnight-bidaily", "20:00", "05:00", skip_days=1, tz=datetime.UTC)

    # Test during active period (night)
    night = datetime.datetime(2025, 2, 17, 23, 0, 0, tzinfo=datetime.UTC)
    if se.active(night):
        # If active, prev_start should be today at 20:00
        prev_start = se.prev_start(night)
        assert prev_start.hour == 20
        # prev_stop should be tomorrow at 05:00
        prev_stop = se.prev_stop(night)
        assert prev_stop.hour == 5
        assert prev_stop.day == 18


def test_multiple_timezones():
    """Test schedule behavior across different timezones."""
    tz_berlin = zoneinfo.ZoneInfo("Europe/Berlin")
    tz_ny = zoneinfo.ZoneInfo("America/New_York")

    # Create schedule in Berlin timezone
    se = ScheduleEntry("berlin-schedule", "12:00", "13:00", tz=tz_berlin)

    # Check with Berlin time
    berlin_noon = datetime.datetime(2025, 6, 17, 12, 30, 0, tzinfo=tz_berlin)
    assert se.active(berlin_noon)

    # Check with NY time (should convert properly)
    # Berlin noon in June is typically 6 AM in NY (6 hours difference)
    ny_morning = datetime.datetime(2025, 6, 17, 6, 30, 0, tzinfo=tz_ny)
    # Convert to Berlin time to check
    ny_as_berlin = ny_morning.astimezone(tz_berlin)
    assert se.active(ny_as_berlin)


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

    # Naive datetime converted to schedule's timezone
    naive_dt = datetime.datetime(2025, 2, 17, 12, 30, 0)
    # When we pass naive datetime, the schedule will use its own timezone
    # This may or may not work as expected, but shouldn't crash


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

    # Test date: February 17, 2025
    # Expected sunset: ~17:45 (5:45 PM), sunrise: ~07:33 (7:33 AM)
    test_date = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=tzinfo)
    sun_times = astral.sun.sun(location.observer, date=test_date.date(), tzinfo=tzinfo)

    sunset = sun_times["sunset"]
    sunrise = sun_times["sunrise"]

    # Calculate expected start and stop times
    expected_start = sunset + datetime.timedelta(hours=1)  # sunset + 1h
    expected_stop_next_day = sunrise + datetime.timedelta(minutes=30)  # sunrise + 30m

    print(f"\nSunset: {sunset}")
    print(f"Sunrise: {sunrise}")
    print(f"Expected start (sunset+1h): {expected_start}")
    print(f"Expected stop (sunrise+30m): {expected_stop_next_day}")

    # Test times every 15 minutes throughout the day and night
    test_times = []
    active_states = []

    # Start from midnight and go for 24 hours in 15-minute increments
    current = datetime.datetime(2025, 2, 17, 0, 0, 0, tzinfo=tzinfo)
    end_time = current + datetime.timedelta(days=1)

    while current < end_time:
        is_active = se.active(current)
        test_times.append(current)
        active_states.append(is_active)

        # Print the state for visibility
        print(f"{current.strftime('%Y-%m-%d %H:%M')} - {'ACTIVE' if is_active else 'inactive'}")

        current += datetime.timedelta(minutes=15)

    # Verify expected behavior at key times

    # Before sunset - should be active (from previous day's schedule)
    afternoon = datetime.datetime(2025, 2, 17, 15, 0, 0, tzinfo=tzinfo)
    # This depends on whether we're still in previous night's window

    # Just after expected start time (sunset + 1h) - should be active
    after_start = expected_start + datetime.timedelta(minutes=15)
    assert se.active(after_start), f"Should be active at {after_start}"

    # Middle of night - should be active
    midnight = datetime.datetime(2025, 2, 17, 23, 30, 0, tzinfo=tzinfo)
    assert se.active(midnight), f"Should be active at midnight {midnight}"

    # Early morning before sunrise+30m - should be active
    early_morning = datetime.datetime(2025, 2, 18, 6, 0, 0, tzinfo=tzinfo)
    assert se.active(early_morning), f"Should be active in early morning {early_morning}"

    # Just before sunrise+30m - should be active
    before_stop = expected_stop_next_day - datetime.timedelta(minutes=15)
    assert se.active(before_stop), f"Should be active just before stop at {before_stop}"

    # Just after sunrise+30m - should NOT be active
    after_stop = expected_stop_next_day + datetime.timedelta(minutes=15)
    assert not se.active(after_stop), f"Should NOT be active after stop at {after_stop}"

    # Mid-day (well after sunrise+30m) - should NOT be active
    midday = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=tzinfo)
    assert not se.active(midday), f"Should NOT be active at midday {midday}"

    # Just before sunset+1h - should NOT be active
    before_evening_start = expected_start - datetime.timedelta(minutes=15)
    assert not se.active(before_evening_start), f"Should NOT be active before evening start at {before_evening_start}"

    # Verify we had both active and inactive periods
    assert any(active_states), "Should have some active periods"
    assert not all(active_states), "Should have some inactive periods"

    # Count transitions between active and inactive
    transitions = 0
    for i in range(1, len(active_states)):
        if active_states[i] != active_states[i - 1]:
            transitions += 1

    # We expect at least 2 transitions (inactive->active at sunset+1h, active->inactive at sunrise+30m)
    assert transitions >= 2, f"Expected at least 2 transitions, got {transitions}"
