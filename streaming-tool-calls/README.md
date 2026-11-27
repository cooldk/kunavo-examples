# Streaming tool-call fixture lab

An offline way to understand why a streamed tool call can be hard to assemble. It contains synthetic Chat Completions SSE captures and a small diagnostic reader. Run the examples without an API key, account, dependencies, or network connection.

Maintained by Kunavo, with AI assistance. All captures are invented test data. This is a protocol teaching example, **not a test of Kunavo, Open WebUI, a model, or any other live client or gateway**.

## Run

Requires Node.js 20.11 or newer; verified with Node.js 26.3.0 on 2026-11-27. No package installation is needed.

```sh
node demo.mjs
node --test test.mjs
node inspect-file.mjs fixtures/complete-tools.sse
node inspect-file.mjs fixtures/missing-tool-index.sse
node inspect-file.mjs fixtures/truncated-tools.sse
```

The demo feeds captures through arbitrary byte boundaries, including boundaries inside UTF-8 characters. It exits nonzero if a fixture's diagnosis differs from its expectation. The 17 tests also cover one-byte chunks, LF/CRLF/CR, interleaved calls, legitimate audio tail metadata, refusal deltas, and the local-file/stdin interface.

## Three observations worth separating

1. **Each tool delta has its own index.** `choices[0].index` identifies a choice; `choices[0].delta.tool_calls[0].index` identifies a tool call within it. A delta that lacks its tool index cannot be reliably assigned by this reader. Two tools may arrive interleaved.
2. **Argument fragments are strings, not standalone JSON documents.** Accumulate them by tool index. The example attempts JSON parsing only after an observed `tool_calls` finish reason and `[DONE]`. That conservative rule is a choice of this lab. A partial fragment is not itself an invalid JSON argument document.
3. **Stream termination and generation outcome answer different questions.** `length` can end a tool argument halfway through, while `content_filter` can omit content. Neither is automatically a schema violation. EOF alone does not tell us whether a capture was complete. Missing terminal metadata produces a warning, not an accusation that an endpoint failed.

Open WebUI's [blank-tool-reply troubleshooting guide](https://docs.openwebui.com/troubleshooting/connection-error/#blank-replies-when-the-model-uses-a-tool) explains why the nested tool index matters to its accumulator. These fixtures let you inspect that shape before spending time on a live setup. They do not reproduce or test Open WebUI itself.

## Expected results

| Synthetic capture | Diagnosis | Meaning within this lab |
| --- | --- | --- |
| `complete-tools.sse` | `tool_calls_assembled` | Two interleaved argument strings parse as JSON after the expected terminal markers. |
| `missing-tool-index.sse` | `schema_or_input_issue` | Tool delta lacks the index used for accumulation. The surrounding choice index does not replace it. |
| `truncated-tools.sse` | `completion_unconfirmed` | The capture has no observed finish reason or `[DONE]`; only warnings. |
| `length-limited.sse` | `generation_truncated` | The observed finish reason is `length`, even though `[DONE]` is present. |
| `unterminated-event.sse` | `completion_unconfirmed` | The final data line lacks a blank-line event boundary; it is not treated as an observed terminal event. |
| `midstream-error.sse` | `stream_error` | A synthetic structured error appears after partial text. |
| `complete-text.sse` | `text_complete` | Text, `stop`, and `[DONE]` were observed in the supported shape. |
| `terminal-without-done.sse` | `terminal_without_done` | `stop` was observed but `[DONE]` was not; a warning. |

`tool_calls_assembled` means only that the lab reconstructed parseable argument JSON. It does **not** validate the tool's JSON schema, check argument safety, authorize an action, execute a tool, or prove that a subsequent assistant turn will work. Generated arguments still need validation against the tool's actual schema and application policy.

## Inspect a local redacted capture

```sh
node inspect-file.mjs ./redacted-capture.sse
node inspect-file.mjs - < ./redacted-capture.sse
```

The command accepts a local regular file or stdin, with a 1 MiB processing limit. It does not fetch URLs, read environment variables, upload data, call a model, or execute tools. Its output contains only the diagnosis, terminal metadata, number of tool calls, and fixed diagnostic codes. It omits response text, call IDs, function names, argument strings, unknown finish-reason values, and exception paths.

Only inspect files you are allowed to use. Redact credentials, private prompts, personal data, and tool arguments before sharing a capture. The tool does not redact or rewrite the input file. The demo prints invented content; the exported JavaScript reader returns assembled data in memory for tests. Use the summary-only CLI for your own files.

The CLI returns exit code 2 for missing arguments, unreadable/nonregular files, or files already known to exceed the size limit. A diagnosis is otherwise JSON data, not a shell pass/fail verdict. Check `outcome` and `diagnostics`; malformed stdin and inputs that exceed the limit while reading are reported there.

## Scope and interpretation

- Supported: UTF-8 SSE framing, one Chat Completions choice at index 0, text deltas, and function tool-call deltas. Empty `choices` events such as usage-only frames are accepted but their usage fields are not analyzed.
- Out of scope: Responses API events, native Messages streams, legacy `function_call`, custom tools, refusal/audio/image output, multiple choices, reconnect behavior, HTTP status/headers, retries, authentication, billing, model quality, and complete schema validation. Unsupported shapes receive a diagnostic; this is not a claim that those shapes are invalid APIs.
- `[DONE]` is recognized by the Chat Completions SDK; it is not part of the general SSE standard. This lab requires it for its own strongest completion labels. A sanitized or partial capture may omit it, and other protocols terminate differently.
- An SSE event is dispatched at a blank line. This reader leaves an unterminated trailing event unconfirmed. It does not assert that every client treats EOF identically or that every missing terminator is an endpoint defect.
- Extra data after `[DONE]` is ignored with a diagnostic. Diagnostics describe this input and reader, not the health of the source service.

## Primary references

Checked 2026-11-27:

- [WHATWG SSE parsing](https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream): UTF-8, line endings, data lines, and event dispatch.
- [Chat Completions types in the official Node SDK](https://github.com/openai/openai-node/blob/master/src/resources/chat/completions/completions.ts): required tool-delta `index`, optional fragment fields, finish-reason meanings, and argument-validation caveats.
- [Official SDK SSE reader](https://github.com/openai/openai-node/blob/master/src/core/streaming.ts): recognition of `[DONE]` and handling of structured API errors. This lab does not import or test that SDK.
- [Open WebUI troubleshooting](https://docs.openwebui.com/troubleshooting/connection-error/#blank-replies-when-the-model-uses-a-tool): the concrete nested-index problem that motivated this example.

For a later live integration, consult the service's current authentication and streaming documentation and validate its actual output separately. Kunavo's [public documentation](https://kunavo.com/docs/authentication?utm_source=github&utm_medium=developer_content&utm_campaign=streaming_tools_20261127) is one starting point; no live compatibility result is included here.
