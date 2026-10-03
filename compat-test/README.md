# OpenAI-compatible endpoint check

One file, no dependencies (Node 18+). It tells you whether an endpoint behaves the way OpenAI-compatible clients assume — before you find out from a client's error message.

```bash
node compat-test.mjs --base-url https://api.kunavo.com/v1 --key sk-kn-... --model claude-sonnet-5
# any other provider works the same way:
node compat-test.mjs --base-url https://example.com/v1 --key ... --model some-model --json report.json
```

| Check | Passes when |
|---|---|
| base URL | `GET /models` returns JSON with a `data[]` list (an HTML page means the `/v1` is missing) |
| auth errors | a wrong key gets `401` with a JSON error body |
| chat | a completion has text, and `usage.total_tokens = prompt + completion` |
| streaming | SSE chunks arrive, a `finish_reason` is set, the stream ends with `[DONE]`; time to first byte and total time are printed |
| stream usage | `stream_options.include_usage` yields a usage chunk |
| tools | a forced tool call returns JSON-parsable `arguments` |
| json mode | `response_format: json_object` returns parsable JSON |
| bad model | an unknown model id gets a `4xx` JSON error |

Your key goes only to `--base-url`, only in the `Authorization` header, and is never printed or written to the report. Every request is capped at 64 output tokens. If the key or the base URL is rejected, the run stops there instead of failing eight times.
