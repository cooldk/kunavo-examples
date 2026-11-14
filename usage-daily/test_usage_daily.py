import copy
import json
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from usage_daily import previous_week, daily_rows


class DailyUsageTest(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(Path(__file__).with_name("usage-fixture.json").read_text())
        self.start, self.end = date(2026, 11, 7), date(2026, 11, 13)

    def test_subcent_exact_sum_and_missing_days(self):
        rows = daily_rows(self.payload, self.start, self.end)
        self.assertEqual(sum(cost for _, cost in rows), Decimal("0.300001"))
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[2], (date(2026, 11, 9), Decimal("0")))

    def test_japan_date_does_not_define_utc_window(self):
        now = datetime.fromisoformat("2026-11-14T00:30:00+09:00")
        self.assertEqual(previous_week(now), (date(2026, 11, 6), date(2026, 11, 12)))

    def test_empty_successful_response_has_seven_zero_days(self):
        self.payload["data"] = []
        self.assertEqual(daily_rows(self.payload, self.start, self.end)[-1],
                         (self.end, Decimal("0")))

    def test_invalid_shape_never_turns_into_zero_report(self):
        for change in ["float", "nan", "duplicate", "model", "window", "timezone", "out_of_window"]:
            p = copy.deepcopy(self.payload)
            if change == "float": p["data"][0]["cost_usd"] = 0.1
            elif change == "nan": p["data"][0]["cost_usd"] = "NaN"
            elif change == "duplicate": p["data"].append(p["data"][0])
            elif change == "model": p["data"][0]["model"] = "synthetic-model"
            elif change == "window": p["end_date"] = "2026-11-12"
            elif change == "timezone": p["data"][0]["bucket_start"] = "2026-11-07T00:00:00"
            elif change == "out_of_window": p["data"][0]["bucket_start"] = "2026-11-06T00:00:00Z"
            with self.subTest(change=change), self.assertRaises(ValueError):
                daily_rows(p, self.start, self.end)


if __name__ == "__main__":
    unittest.main()
