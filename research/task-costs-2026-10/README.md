# What 270 LLM tasks cost on one gateway

Published by Kunavo's operator on 2026-10-03. This is a small, first-party task-cost study, not an independent model ranking or an uptime benchmark. Runs took place on 2026-10-01, through Kunavo only, from one client location.

## Results

All 270 task runs and 265 request attempts are included. The gateway recorded and billed 263 requests; two HTTP 502 attempts were absent from its usage logs and were recovered by task retries. Total billed cost was approximately **$0.82**.

| Model | Concurrency | Task | Successes | Total USD | USD per success |
|---|---:|---|---:|---:|---:|
| Claude Sonnet 5 | 1 | Code repair | 30/30 | 0.2769 | 0.0092 |
| Claude Sonnet 5 | 5 | Code repair | 30/30 | 0.2268 | 0.0076 |
| GPT-6 Sol | 1 | Code repair | 30/30 | 0.0499 | 0.0017 |
| Claude Sonnet 5 | 1 | Extraction | 30/30 | 0.0930 | 0.0031 |
| Claude Sonnet 5 | 5 | Extraction | 30/30 | 0.1068 | 0.0036 |
| GPT-6 Sol | 1 | Extraction | 30/30 | 0.0171 | 0.0006 |
| Claude Sonnet 5 | 1 | FAQ workflow | 27/30 | 0.0215 | 0.0008 |
| Claude Sonnet 5 | 5 | FAQ workflow | 26/30 | 0.0228 | 0.0009 |
| GPT-6 Sol | 1 | FAQ workflow | 27/30 | 0.0083 | 0.0003 |

Cost per success means **all billed attempts / successful tasks**, including failed tasks and retries. Dollar values reflect this gateway's prices at sampling time, not official-provider prices. The six-row comparison in the accompanying article uses concurrency 1; the 270-run total also includes Sonnet at concurrency 5.

## Download and reproduce the arithmetic

- [Request and task records](runs/) — JSONL, with statuses, task outcomes, timing and usage.
- [Billed requests](runs/billing.json) — request tags, token counts and charged USD; no account identifiers, keys or customer data.
- [Machine-readable summary](runs/summary.json).
- [Frozen input definitions](PREREG.md) and [detailed report](REPORT.md), in Chinese.
- [Harness](run_b02.py) and [summarizer](summarize.py).
- [Source checksums](SOURCE-SHA256.json). These copied files are unchanged from the source study.

From this directory, run `python3 summarize.py` to rebuild `runs/summary.json`. This uses only the downloaded data and makes no API calls. The source plan was committed internally at 2026-10-01 13:38Z (`a4aea5f`), before sampling at 13:39–14:10Z. That is a publisher-provided provenance record, not a claim of public preregistration. The internal protocol linked from the original PREREG file is not included here; the complete run-specific rules are in PREREG itself.

## Method and limits

Code repair uses 30 Python programs from [QuixBugs](https://github.com/jkoppel/QuixBugs), pinned to the commit in `code-repair-programs.json`. Extraction uses RFCs 9500–9529 and labels from the [RFC Editor index](https://www.rfc-editor.org/rfc-index.xml). The workflow uses 30 synthetic questions and a six-entry FAQ. Success rules, retries and the full run matrix are in PREREG.

QuixBugs has been public for years and may be in training data. There are only 30 tasks per group. There is no direct Anthropic/OpenAI control, no other gateway comparison, and no repeat-day sampling. The workflow measures both retrieval and generation: six of its ten failures came from retrieval. The original validator also had a flaw; that historical result is preserved rather than retroactively corrected.

The output-token difference is observed; its exact division into visible answer and internal reasoning is not established by these records. Do not interpret it as proof of how either model reasons.

## Running new experiments

Python 3 standard library is used for requests. Code repair also requires Docker and a local `kn-b02-py` image containing Python 3.12, pytest 8.3.3 and pytest-timeout 2.3.1. Fetch the pinned QuixBugs checkout and RFC text inputs yourself, then use the harness's `--quixbugs` and `--rfc-dir` options. Set `KUNAVO_BASE_URL` to an OpenAI-compatible `/v1` URL and `KUNAVO_API_KEY` to your own key.

New runs incur the chosen provider's API charges. Collect that provider's own usage export for billing; the production database readback script is intentionally not distributed. Re-running against newer model versions may produce different results.

The harness preserves the historical network-disabled Docker invocation. It is a research starting point; review the container isolation before executing untrusted model-generated code.
