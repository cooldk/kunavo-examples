# Daily usage CSV: UTC boundaries, decimal costs and missing days

A standard-library Python example for turning a single key's usage snapshot into a daily CSV. Maintained by Kunavo's operator; code and documentation were prepared with AI assistance. The offline fixture and tests were run with Python 3.9.6 on 2026-11-14. No live API call is part of that validation.

## Try it without an account or key

```sh
cd usage-daily
python3 usage_daily.py usage-fixture.json
python3 -m unittest -v test_usage_daily.py
```

The fixture is synthetic and contains only the response fields used by this example. It is not customer spending or a price quote. The CSV has seven daily rows, including four missing days filled with zero; the total is exactly `0.300001` USD. Four tests cover sub-cent sums, missing days, UTC/Japan date boundaries, an empty successful response, and rejection of malformed or duplicate input.

## Read your own usage

Set `KUNAVO_API_KEY` in the process environment through your normal secret-management workflow, then run:

```sh
python3 usage_daily.py > usage.csv.tmp && mv usage.csv.tmp usage.csv
```

This makes one read-only `GET https://api.kunavo.com/v1/usage` request for the previous seven completed UTC days, with `bucket=day` and no `group_by`. It does not generate model output. Each key can query only its own usage. See the [Usage API reference](https://kunavo.com/docs/usage?utm_source=github&utm_medium=example&utm_campaign=usage_daily_20261114) for authentication and the response contract.

## Choices and limits

- Inclusive start/end dates are calculated in UTC. At 00:30 in Japan on November 14, the latest completed UTC day is November 12. UTC daily buckets cannot simply be relabeled as Japanese calendar days.
- `cost_usd` is parsed directly from its string into `Decimal`. Inexact addition fails instead of silently rounding. The API's existing six-decimal response precision cannot be recovered or improved by this conversion.
- Missing days become zero only after the response window and bucket are checked. HTTP errors and unexpected input fail the command, preserving the previous CSV when using the shell command above.
- A duplicate day or model-grouped row is rejected; this example expects one ungrouped row per day. To support model grouping, change the data key and aggregation deliberately.
- A response is a snapshot. Replace previously saved `(key ID, UTC day)` values; do not append overlapping snapshots and sum them. Never use a secret API key as a log label.
- This is usage reporting for one key, not a wallet ledger, invoice, refund calculation, organization total, or audit of final settlement. Completed days may still require re-querying and reconciliation for delayed records or later corrections.

The small script is an instructional example, not a complete accounting system. No model prices are embedded.
