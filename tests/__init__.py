import datetime
import unittest
import zoneinfo

import astral

from scheduleparse import ScheduleEntry


class TestScheduleEntry(unittest.TestCase):
    def test_on(self):
        se = ScheduleEntry("on", "00:00", "24:00")
        self.assertTrue(se.active())

    def test_off(self):
        se = ScheduleEntry("off", "00:00", "00:00")
        self.assertFalse(se.active())

    def test_fixed(self):
        now = datetime.datetime(2025, 2, 17, 12, 00, 00, tzinfo=datetime.UTC)
        se = ScheduleEntry("fixed", "12:00", "12:05", tz=now.tzinfo)
        self.assertTrue(se.active(now))

        # test prev and next are equal, if we hit the exact start ts
        self.assertEqual(se.prev_start(now), now)
        self.assertEqual(se.next_start(now), now)
        self.assertEqual(se.prev_stop(now), now + datetime.timedelta(minutes=5))
        self.assertEqual(se.next_stop(now), now + datetime.timedelta(minutes=5))

    def test_over_night(self):
        now = datetime.datetime(2025, 2, 17, 3, 00, 00, tzinfo=datetime.UTC)
        day = datetime.datetime(2025, 2, 17, 9, 00, 00, tzinfo=datetime.UTC)
        se = ScheduleEntry("over_night", "20:00", "05:00", tz=now.tzinfo)
        self.assertTrue(se.active(now))
        self.assertFalse(se.active(day))

    def test_now(self):
        now = datetime.datetime.now().astimezone()
        start = (now - datetime.timedelta(minutes=5)).strftime("%H:%M")
        end = (now + datetime.timedelta(minutes=5)).strftime("%H:%M")
        se = ScheduleEntry("now", start, end, tz=now.tzinfo)
        self.assertTrue(se.active(now))

    def test_tz(self):
        tz = zoneinfo.ZoneInfo("Europe/Berlin")
        now = datetime.datetime(2025, 2, 17, 12, 00, 00, tzinfo=tz)
        se = ScheduleEntry("tz", "12:00", "12:05", tz=tz)
        self.assertTrue(se.active(now))

    def test_astral(self):
        tzname = "Europe/Berlin"
        tzinfo = zoneinfo.ZoneInfo(tzname)
        coelbe = astral.LocationInfo("Coelbe", "Germany", tzname, 50.85318, 8.78735)
        se = ScheduleEntry("daytime", "sunrise+00:00", "sunset-00:00", location=coelbe, tz=tzinfo)

        lunch = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=tzinfo)
        self.assertTrue(se.active(lunch))
        afterwork = datetime.datetime(2025, 2, 17, 18, 0, 0, tzinfo=tzinfo)
        self.assertFalse(se.active(afterwork))
        morning_coffee = datetime.datetime(2025, 2, 17, 8, 0, 0, tzinfo=tzinfo)
        self.assertTrue(se.active(morning_coffee))

        sunrise = datetime.datetime.fromisoformat("2025-02-17 07:33:26.860012+01:00")
        sunset = datetime.datetime.fromisoformat("2025-02-17 17:44:59.100299+01:00")
        self.assertEqual(se.prev_start(lunch), sunrise)
        self.assertEqual(se.prev_stop(lunch), sunset)

    def test_skip(self):
        se = ScheduleEntry("bidaily", "00:00", "24:00", skip_days=1, tz=datetime.UTC)

        now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
        self.assertTrue(se.active(now))
        self.assertEqual(se.prev_start(now), datetime.datetime.fromisoformat("2025-02-17 00:00:00+00:00"))
        self.assertEqual(se.prev_stop(now), datetime.datetime.fromisoformat("2025-02-18 00:00:00+00:00"))
        self.assertEqual(se.next_start(now), datetime.datetime.fromisoformat("2025-02-19 00:00:00+00:00"))
        self.assertEqual(se.next_stop(now), datetime.datetime.fromisoformat("2025-02-20 00:00:00+00:00"))

        tomorrow = datetime.datetime(2025, 2, 18, 12, 0, 0, tzinfo=datetime.UTC)
        self.assertFalse(se.active(tomorrow))

    def test_repr(self):
        se = ScheduleEntry("bidaily", "00:00", "24:00")
        se_repr = str(se)
        se2 = eval(se_repr)

        now = datetime.datetime(2025, 2, 17, 12, 0, 0, tzinfo=datetime.UTC)
        self.assertEqual(se.next_start(now), se2.next_start(now))


if __name__ == "__main__":
    unittest.main()
