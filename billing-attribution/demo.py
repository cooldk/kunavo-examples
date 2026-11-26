"""Synthetic SQLite lesson: membership can change; booked cost attribution cannot.

No network, credentials, customer data or production database access.
This is a teaching schema, not Kunavo's production implementation.
"""
import sqlite3
from decimal import Decimal

UNITS_PER_DOLLAR = 100_000_000


def database():
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
      CREATE TABLE client_groups (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0
      );
      CREATE TABLE api_keys (
        id TEXT PRIMARY KEY,
        group_id TEXT REFERENCES client_groups(id),
        revoked INTEGER NOT NULL DEFAULT 0
      );
      CREATE TABLE booked_costs (
        event_id TEXT PRIMARY KEY,
        key_id TEXT NOT NULL REFERENCES api_keys(id),
        group_id TEXT REFERENCES client_groups(id),
        cost_units INTEGER NOT NULL CHECK(cost_units >= 0)
      );
    """)
    return db


def book(db, event_id, key_id, cost_units):
    """Book a synthetic completed charge under membership at this operation.

    INSERT SELECT captures the group once. Real asynchronous systems must define
    their attribution instant and transaction boundary explicitly.
    """
    if type(cost_units) is not int or cost_units < 0:
        raise ValueError("cost_units must be a nonnegative integer")
    cursor = db.execute("""
      INSERT INTO booked_costs(event_id, key_id, group_id, cost_units)
      SELECT ?, id, group_id, ? FROM api_keys WHERE id = ? AND revoked = 0
    """, (event_id, cost_units, key_id))
    if cursor.rowcount != 1:
        raise ValueError("unknown or revoked synthetic key")


def historical_totals(db):
    return dict(db.execute("""
      SELECT group_id, SUM(cost_units) FROM booked_costs GROUP BY group_id
    """))


def current_membership_totals(db):
    """Deliberately wrong for historical attribution; useful as a regression case."""
    return dict(db.execute("""
      SELECT k.group_id, SUM(c.cost_units)
      FROM booked_costs c JOIN api_keys k ON k.id = c.key_id
      GROUP BY k.group_id
    """))


def dollars(units):
    return format(Decimal(units) / Decimal(UNITS_PER_DOLLAR), ".8f")


def scenario():
    db = database()
    db.executemany("INSERT INTO client_groups(id,name) VALUES (?,?)",
                   [("client-a", "Client A"), ("client-b", "Client B")])
    db.execute("INSERT INTO api_keys(id,group_id) VALUES ('key-1','client-a')")
    book(db, "event-1", "key-1", 300_000_000)
    db.execute("UPDATE api_keys SET group_id='client-b' WHERE id='key-1'")
    book(db, "event-2", "key-1", 200_000_000)
    return db


if __name__ == "__main__":
    with scenario() as connection:
        for label, query in [("Wrong: current membership", current_membership_totals),
                             ("Correct: booked group", historical_totals)]:
            print(label)
            for group, units in sorted(query(connection).items()):
                print(f"  {group}: ${dollars(units)}")
