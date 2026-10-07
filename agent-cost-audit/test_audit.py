import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path
from audit import audit


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(Path(__file__).with_name("example.json").read_text())

    def test_retries_and_rejected_work_stay_in_cost(self):
        got = audit(self.fixture)
        self.assertEqual(got["work_attempts"], 3)
        self.assertEqual(got["accepted_work_tasks"], 1)
        self.assertEqual(Decimal(got["work_estimated_usd"]), Decimal("0.288"))
        self.assertEqual(Decimal(got["work_cost_per_accepted_task_usd"]), Decimal("0.288"))
        self.assertEqual(got["healthcheck_estimated_usd"], "0.000039")
        self.assertEqual(got["tasks"][0]["cache_read_fraction_of_input"], "0.45")

    def test_no_accepted_task_is_unknown_not_free(self):
        self.fixture["tasks"][0]["accepted"] = False
        self.assertIsNone(audit(self.fixture)["work_cost_per_accepted_task_usd"])

    def test_zero_input_has_no_cache_fraction(self):
        self.fixture["tasks"][0]["attempts"] = [dict.fromkeys(("uncached_input", "cache_write", "cache_read", "output"), 0)]
        self.assertIsNone(audit(self.fixture)["tasks"][0]["cache_read_fraction_of_input"])

    def test_rejects_missing_negative_and_boolean_tokens(self):
        for bad in (-1, True, 1.5, None):
            data = copy.deepcopy(self.fixture)
            data["tasks"][0]["attempts"][0]["uncached_input"] = bad
            with self.assertRaises(ValueError):
                audit(data)

    def test_rejects_bad_rates(self):
        for bad in ("NaN", "Infinity", "-1", None):
            data = copy.deepcopy(self.fixture)
            data["prices_usd_per_million"]["cache_read"] = bad
            with self.assertRaises(ValueError):
                audit(data)

    def test_rejects_duplicate_tasks_and_accepted_healthcheck(self):
        duplicate = copy.deepcopy(self.fixture)
        duplicate["tasks"].append(duplicate["tasks"][0])
        with self.assertRaises(ValueError):
            audit(duplicate)
        self.fixture["tasks"][2]["accepted"] = True
        with self.assertRaises(ValueError):
            audit(self.fixture)


if __name__ == "__main__":
    unittest.main()
