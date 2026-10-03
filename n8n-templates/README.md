# n8n workflows with validation and human review

Import one of these JSON files into n8n, then configure the model and your own credentials. They use the built-in OpenAI credential with a configurable base URL and model; Kunavo is optional. No API keys, saved executions or customer data are included.

| Workflow | What it does | Configure before activation |
|---|---|---|
| [Extract and validate contact details](01-extract-and-validate.json) | Parses form text, validates the result, retries once, then asks the submitter for missing details | Model credential and model id |
| [Draft FAQ support replies](02-support-replies-from-faq.json) | Matches a local FAQ, drafts a reply, and lets a reviewer approve, edit or escalate | Your FAQ, model, reviewer notification and delivery action |
| [Draft posts from RSS](03-rss-to-reviewed-drafts.json) | Drafts up to three new feed items per run, then asks a reviewer to approve, edit or skip each | Feed URL, model, reviewer notification and draft destination |

The notification, delivery and storage placeholders must be replaced with your own integrations. In particular, send `$execution.resumeFormUrl` only to the intended reviewer; treat that review link as private. The FAQ workflow acknowledges a webhook immediately and keeps the review form separate from the customer's browser.

The RSS template marks the feed items as seen before selecting up to three. Extra items on that run are skipped, not queued. Adjust this if you need a backlog.

## Validation

The workflows were exercised on n8n 2.41.4 on 2026-10-01 using a real Kunavo endpoint and Claude Sonnet 5: extraction success, missing-contact fallback, FAQ approval/edit/escalation, RSS approval/edit/skip and repeat-run deduplication. Other providers and versions may behave differently. The JSON-object guard was tightened on 2026-10-03 and checked locally with null, array, scalar, malformed and valid model outputs.

GitHub distribution is available now. These files have **not yet been accepted into the n8n official template library**.

## Reproduce the JSON

```bash
mkdir -p /tmp/kunavo-n8n-test-copies
python3 gen_templates.py . /tmp/kunavo-n8n-test-copies
```

The second directory receives test copies with a placeholder credential id; it does not contain a key. Only the three numbered JSON files in this directory are intended for distribution.

Optional [Kunavo setup guide](https://kunavo.com/docs/integrations/n8n?utm_source=github&utm_medium=template&utm_campaign=i06-n8n). The repository is maintained by Kunavo's operator.
