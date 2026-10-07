# Count the cost of an accepted agent task

[中文教程](README.zh-CN.md)

An offline Python example for coding agents and scheduled assistants. It adds cache writes, cache reads, retries and rejected work, while reporting health checks separately. No API key, account, network requests or dependencies are needed.

Maintained by the Kunavo team. Code and writing were AI-assisted. The example uses **synthetic data and hypothetical prices**, not customer records or a live provider benchmark.

## Run

Python 3.9 or later, from the repository root:

```sh
python3 agent-cost-audit/audit.py agent-cost-audit/example.json
python3 -m unittest discover -s agent-cost-audit -p 'test_*.py'
```

The fixture has two work tasks and one health check. The first task takes two attempts and is accepted; the second is rejected after one attempt.

| Result | Expected |
|---|---:|
| Work attempts | 3 |
| Accepted work tasks | 1 |
| Estimated work cost | $0.288 |
| Estimated health-check cost | $0.000039 |
| Work cost per accepted task | $0.288 |

Dividing the work cost by three API attempts would give $0.096. That measures a different unit. The rejected task and the extra attempt still consumed resources. If no task is accepted, cost per accepted task is `null`, not zero. Acceptance must come from your own check: tests passing, a reviewed answer, or another explicit completion criterion. An HTTP 200 alone is not that check.

## Normalize input before calculating

Every attempt has four **disjoint** token buckets: `uncached_input`, `cache_write`, `cache_read`, `output`. Supply all four, including measured zeroes. Missing usage is unknown; do not convert a timeout with missing usage into a free call.

- Anthropic Messages reports ordinary `input_tokens`, `cache_creation_input_tokens` and `cache_read_input_tokens` separately. Add those three for total input.
- OpenAI-style usage generally reports total input plus detail fields. Subtract the reported cache-read and, where applicable, cache-write subsets to obtain ordinary input. Inspect the actual endpoint schema before mapping.
- A gateway may normalize fields differently. Read its documented response and compare a sample with the billed usage record. Do not apply both normalization rules to the same record.

The tool intentionally accepts a normalized file rather than guessing the format. Do not double-count cumulative streaming usage events: each `attempt` must represent one actual request, using its final usage record.

## The arithmetic

For counts U (ordinary input), W (cache write), R (cache read), O (output), and their USD prices per million tokens:

```text
attempt_cost = (U*pU + W*pW + R*pR + O*pO) / 1,000,000
cache_read_fraction = sum(R) / sum(U + W + R)
work_cost_per_accepted_task = all_work_attempt_cost / accepted_work_task_count
```

The cache metric weights token volume across attempts; it is not the average of per-call percentages. Health-check costs remain in `total_estimated_usd` but do not count as accepted work.

## Before using your own numbers

1. Keep the same completion criterion and complete observation window when comparing runs.
2. Include failed/rejected work and retries whenever they incurred token charges. Resolve missing usage against billing first.
3. Replace every sample rate with your applicable tariff. This small example supports one rate per bucket per file. Run different models, cache-write TTLs, pricing tiers or discounts separately; combine their costs afterward and deduplicate accepted task IDs across files. Never add per-model accepted-task denominators for a task that spans models.
4. Check the provider bill. Tool fees, media generation, hosting, taxes, refunds and credits are outside this token-only estimate. A wallet top-up is not measured task cost.
5. Retain your source usage and tariff timestamp privately. Do not commit private prompts, API keys or customer identifiers to this public repository.

Validation rejects missing/noninteger/negative token counts, nonfinite/negative prices, duplicate task IDs and health checks marked as accepted work.

## Sources and integration references

Usage semantics checked on 2026-10-07:

- [Anthropic: prompt caching and usage fields](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [OpenAI: prompt caching and usage details](https://developers.openai.com/api/docs/guides/prompt-caching)

For Kunavo-specific setup, see [Cline](https://kunavo.com/docs/integrations/cline?utm_source=github&utm_medium=developer_content&utm_campaign=kn_202610_p09) and [OpenCode](https://kunavo.com/docs/integrations/opencode?utm_source=github&utm_medium=developer_content&utm_campaign=kn_202610_p09). This calculator works offline regardless of which provider you use.
