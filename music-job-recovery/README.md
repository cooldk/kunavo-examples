# Recover an asynchronous music job without blindly resubmitting

Maintained by the Kunavo team. Code and writing were AI-assisted and checked with the offline tests below. This is a **decision-planning example**, not an HTTP client, durable queue, live service test or guarantee of exactly-once generation. It makes no network requests and needs no key or paid account.

## Run the fault scenarios

Python 3.9+, standard library only. From the repository root:

```sh
python3 music-job-recovery/recovery.py
python3 -m unittest discover -s music-job-recovery -p 'test_*.py' -v
```

| Synthetic event | Decision |
|---|---|
| Submit response is lost; no task ID | Reuse the original key and identical body inside a bounded recovery window |
| Task ID is known | Poll that ID; do not submit again |
| Task reports `failed` | Inspect the failure; a new generation needs an explicit decision |
| Completed but `output.archived=false` | Arrange a durable copy; do not treat temporary URLs as archived |
| Unknown submission passes the local recovery budget | Reconcile manually; do not rotate the key automatically |
| Poll budget is reached | Pause and keep the ID; the remote task may still be running |

The 10 tests cover these branches, payload changes, mismatched responses, incomplete output, bounded backoff and conflicting terminal states. They test local decisions, **not** server deduplication, billing, audio quality or delivery reliability.

## Records to persist before submitting

For each intended generation, persist a business operation ID, the account/environment, one random idempotency key, the exact request body and its digest, the first attempt time, and later the returned task ID/status/output. `prepare()` builds only the in-memory part of this record. A caller must durably save it **before** sending a request and save every response before advancing. Never save the API credential in this record. The body may contain private lyrics, so restrict access and define retention.

Keep transport retries separate from a creative decision to generate another song. A new intended song gets a new operation/key. Retrying an uncertain submission keeps the original account, key and body. This sample detects local body changes; it does not claim the server rejects same-key/different-body requests.

## Mapping to Kunavo's documented API

Checked against the [music documentation](https://kunavo.com/docs/music?utm_source=github&utm_medium=developer_content&utm_campaign=kn_202610_p13) on 2026-10-09:

- Submit to `POST /v1/audio/music/jobs` with `Idempotency-Key`; a new job returns 202, a replay 200. Persist the returned `msc_*` ID.
- Query `GET /v1/audio/music/jobs/{id}`. Terminal states are `completed` and `failed`; pending states are `queued` and `in_progress`.
- Inspect `output.archived` along with the track URLs. The completed job record and the media URLs have different retention concerns.

The documentation describes an approximate 24-hour replay window. Our **one-hour local budget is a conservative application choice, not a server TTL**. Do not reset its start time at each retry. A network timeout means the result is unknown, not that generation failed. An upstream acceptance followed by a persistence failure can still need reconciliation; idempotency is not a universal exactly-once guarantee.

## What a real worker must add

This planner accepts trusted, internally consistent local state. It does not validate arbitrary untrusted files. Add durable storage and per-operation concurrency control, authentication/account scoping, HTTP status checks, capped retries/jitter and `Retry-After` handling, timeouts, observability, and a controlled output downloader. A 401/403, 404 or validation error is not an invitation to submit a replacement job. Preserve the ID and inspect the cause. The suggested poll delays are 5, 10, 20, then 30 seconds, up to 12 successful pending observations; transport errors need a separate bounded policy.

If you use webhooks, verify signatures and freshness and deduplicate event IDs before acting. This example uses polling decisions only and does not implement webhook receipt or downloading. `record_manifest` means metadata can be recorded; it does not mean a person accepted the song or that a local backup exists.

Use new, self-authored sample inputs when demonstrating this workflow. Do not publish customer prompts, task records or generated media without permission.
