import sqlite3
import unittest
from demo import book, current_membership_totals, dollars, historical_totals, scenario


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.db = scenario()
        self.addCleanup(self.db.close)

    def test_move_preserves_completed_costs_and_exposes_wrong_join(self):
        self.assertEqual(current_membership_totals(self.db), {"client-b": 500_000_000})
        self.assertEqual(historical_totals(self.db),
                         {"client-a": 300_000_000, "client-b": 200_000_000})

    def test_revocation_does_not_erase_booked_cost(self):
        self.db.execute("UPDATE api_keys SET revoked=1 WHERE id='key-1'")
        self.assertEqual(sum(historical_totals(self.db).values()), 500_000_000)
        with self.assertRaises(ValueError):
            book(self.db, "new", "key-1", 1)

    def test_archived_group_and_reused_name_keep_distinct_ids(self):
        self.db.execute("UPDATE client_groups SET archived=1 WHERE id='client-a'")
        self.db.execute("INSERT INTO client_groups(id,name) VALUES ('client-c','Client A')")
        self.db.execute("UPDATE api_keys SET group_id='client-c' WHERE id='key-1'")
        book(self.db, "event-3", "key-1", 1)
        self.assertEqual(historical_totals(self.db),
                         {"client-a": 300_000_000, "client-b": 200_000_000, "client-c": 1})

    def test_ungrouping_only_affects_new_entries(self):
        self.db.execute("UPDATE api_keys SET group_id=NULL WHERE id='key-1'")
        book(self.db, "event-3", "key-1", 1)
        self.assertEqual(historical_totals(self.db)[None], 1)
        self.assertEqual(historical_totals(self.db)["client-b"], 200_000_000)

    def test_duplicate_event_cannot_double_count(self):
        with self.assertRaises(sqlite3.IntegrityError):
            book(self.db, "event-1", "key-1", 300_000_000)
        self.assertEqual(sum(historical_totals(self.db).values()), 500_000_000)

    def test_subcent_precision_and_invalid_amounts(self):
        book(self.db, "event-3", "key-1", 1)
        self.assertEqual(dollars(historical_totals(self.db)["client-b"]), "2.00000001")
        for invalid in [True, -1, 0.1, "1"]:
            with self.assertRaises(ValueError):
                book(self.db, "invalid", "key-1", invalid)


if __name__ == "__main__":
    unittest.main()
