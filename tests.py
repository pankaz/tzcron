# Copyright 2015 Bloomberg Finance L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime as dt
import unittest

import ddt
import pytz

import tzcron


class TestSchedule(unittest.TestCase):
    """
    Test suite for the tzcron module
    """

    def setUp(self):
        self.now = dt.datetime.now(pytz.utc)

    def test_next_minute(self):
        cron_expression = "* * * * * *"
        timezone = pytz.utc
        start = self.now
        testee = tzcron.Schedule(cron_expression, timezone, start)
        next_it = next(testee)

        expected_time = self.now.replace(second=0, microsecond=0)
        expected_time = expected_time + dt.timedelta(0, 60)
        self.assertEqual(str(expected_time), str(next_it))

    def test_next_minute_tz(self):
        cron_expression = "* * * * * *"
        timezone = pytz.timezone('US/Mountain')
        start = self.now
        testee = tzcron.Schedule(cron_expression, timezone, start)
        next_it = next(testee)

        expected_time = self.now.replace(second=0, microsecond=0)
        expected_time = expected_time + dt.timedelta(0, 60)
        expected_time = expected_time.astimezone(timezone)
        self.assertEqual(str(expected_time), str(next_it))

    def test_friday_at_5(self):
        cron_expression = "0 5 * * 5 *"
        timezone = pytz.utc
        start = dt.datetime.strptime('1989-04-24T05:01:00',
                                     "%Y-%m-%dT%H:%M:%S")
        start = start.replace(tzinfo=timezone)
        testee = tzcron.Schedule(cron_expression, timezone, start)
        next_it = next(testee)

        expected_time = dt.datetime.strptime('1989-04-28T05:00:00',
                                             "%Y-%m-%dT%H:%M:%S")
        expected_time = expected_time.replace(tzinfo=timezone)
        self.assertEqual(str(expected_time), str(next_it))

    def test_start_dst(self):
        cron_expression = "30 5 * * * *"
        timezone = pytz.timezone("Europe/London")
        start = dt.datetime.strptime('2015-03-29T00:00:00',
                                     "%Y-%m-%dT%H:%M:%S")
        start = timezone.localize(start, is_dst=False)
        testee = tzcron.Schedule(cron_expression, timezone, start)
        next_it = next(testee)

        expected_time = dt.datetime.strptime('2015-03-29T05:30:00',
                                             "%Y-%m-%dT%H:%M:%S")
        expected_time = timezone.localize(expected_time, is_dst=True)
        self.assertEqual(str(expected_time), str(next_it))

    def test_start_dst_invalid_occurrence(self):
        """Test that tzcron updates the offset when moving to DST"""
        cron_expression = "30 1 * * * *"
        timezone = pytz.timezone("Europe/London")
        start = dt.datetime.strptime('2015-03-29T00:00:00',
                                     "%Y-%m-%dT%H:%M:%S")
        start = timezone.localize(start, is_dst=False)
        testee = tzcron.Schedule(cron_expression, timezone, start)
        self.assertRaises(pytz.NonExistentTimeError,
                          lambda: next(testee))

    def test_end_dst(self):
        cron_expression = "30 5 * * * *"
        timezone = pytz.timezone("Europe/London")
        start = dt.datetime.strptime('2015-10-25T00:00:00',
                                     "%Y-%m-%dT%H:%M:%S")
        start = timezone.localize(start, is_dst=True)
        testee = tzcron.Schedule(cron_expression, timezone, start)
        next_it = next(testee)

        expected_time = dt.datetime.strptime('2015-10-25T05:30:00',
                                             "%Y-%m-%dT%H:%M:%S")
        expected_time = timezone.localize(expected_time, is_dst=False)
        self.assertEqual(str(expected_time), str(next_it))

    def test_end_dst_double_occurrence(self):
        cron_expression = "30 1 * * * *"
        timezone = pytz.timezone("Europe/London")
        start = dt.datetime.strptime('2015-10-25T00:00:00',
                                     "%Y-%m-%dT%H:%M:%S")
        start = timezone.localize(start, is_dst=True)
        testee = tzcron.Schedule(cron_expression, timezone, start)
        self.assertRaises(pytz.AmbiguousTimeError,
                          lambda: next(testee))


@ddt.ddt
class TestInvalidSchedules(unittest.TestCase):
    """Test suite for invalid expressions"""

    def setUp(self):
        self.now = dt.datetime.now(pytz.utc)
        self.timezone = pytz.timezone("Europe/London")

    @ddt.data(
        "",
        "-1 1 * * * *",
        "60 * * * * *",
        "* 24 * * * *",
        "* * 32 * * *",
        "* * * 13 * *",
        "* * * * 8 *",
        "* * * * 0 *",
    )
    def test_invalid_number(self, expression):
        self.assertRaises(tzcron.InvalidExpression, tzcron.Schedule,
                          expression, self.timezone, self.now)

    @ddt.data(
        "* * * LUN * *",
        "* * * mon * *",
        "* * * MON * *",
        "* * * * JAN *",
        "* * * * DOM *",
    )
    def test_invalid_replacements(self, expression):
        self.assertRaises(tzcron.InvalidExpression, tzcron.Schedule,
                          expression, self.timezone, self.now)


@ddt.ddt
class TestSpecificDates(unittest.TestCase):
    """Test suite with multiple expressions for a specific date"""

    def setUp(self):
        self.start = dt.datetime(2016, 5, 31, 12, 30).replace(tzinfo=pytz.utc)
        self.timezone = pytz.timezone("UTC")

    @ddt.data(
        "* * * * 5 *",
        "* * * * FRI *",
        "* * * * fri *",
        "* * * jun Fri *",
        "* * 3 6 FRI *",
        "* * 3 * * *",
        "* * 3 6 * *",
    )
    def test_2016_06_03(self, expression):
        results = tzcron.Schedule(expression, self.timezone, self.start)

        expected_date = dt.datetime(2016, 6, 3).replace(tzinfo=pytz.utc)
        self.assertEqual(next(results), expected_date)

    @ddt.data(
        "* * * * 3 *",
        "* * * * WED *",
        "* * * * wed *",
        "* * * * Wed *",
        "* * 1 * * *",
        "* * * 6 * *",
        "* * * JUN * *",
        "* 0 * * * *",
    )
    def test_2016_06_01(self, expression):
        results = tzcron.Schedule(expression, self.timezone, self.start)

        expected_date = dt.datetime(2016, 6, 1).replace(tzinfo=pytz.utc)
        self.assertEqual(next(results), expected_date)


if __name__ == '__main__':
    unittest.main()
