# Moving a key must not move its booked cost

A small SQLite example for developers building usage billing. It reproduces a
reporting mistake: joining old usage rows to a key's **current** client group.

Maintained by Kunavo's operator, with AI-assisted code and writing. All amounts,
groups and events below are synthetic. This is a teaching schema, not the service's
database or a test of live billing. Python 3 and its standard library are enough;
no key, signup, package installation or API call is needed.

```sh
cd billing-attribution
python3 demo.py
python3 -m unittest -v
```

Expected demo output:

```text
Wrong: current membership
  client-b: $5.00000000
Correct: booked group
  client-a: $3.00000000
  client-b: $2.00000000
```

## The bug is in the join

Key `key-1` records a completed $3 charge in Client A, moves to Client B, then
records a completed $2 charge there. A report that groups by `api_keys.group_id`
now gives all $5 to Client B. The total still adds up, so a whole-account total
check will not catch the error.

The example stores a stable group ID on each booked cost and groups that column:

```sql
SELECT group_id, SUM(cost_units)
FROM booked_costs
GROUP BY group_id;
```

It keeps the mutable group on the key for future work. The historical snapshot
serves a different purpose. Names are display labels, not identity: a newly created
group with a reused name must not inherit an archived group's charges.

## What the six tests cover

- A move exposes the wrong join while preserving historical attribution.
- Revocation blocks new synthetic charges without erasing old ones.
- Archiving a group and reusing its name leaves separate stable IDs.
- Ungrouping a key does not ungroup earlier entries.
- A unique event ID prevents the same entry being booked twice.
- Integer units preserve eight decimal places, including a one-unit charge.

These tests validate the local model only. They do not validate production
concurrency, refunds, taxes, currency conversion, authorization or hard spending
limits. There is no account debit here. A real billing system must combine its
ledger and balance changes atomically and define when asynchronous work is
attributed. Submission time and settlement time can differ; choose explicitly.
This example captures membership at the booking operation.

## Using Kunavo's existing groups

Kunavo's [key groups](https://kunavo.com/docs/key-groups) retain booked usage when
keys move, support group monthly limits and CSV exports, and share one account
balance. They are not separate customer logins or wallets. Check the current
documentation for the product contract; the SQLite schema above is deliberately
independent of it.
