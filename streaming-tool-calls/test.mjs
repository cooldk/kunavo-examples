import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { inspectChatStream } from './inspect.mjs';
import { fixtures, expectedOutcomes, splitBytes, frame } from './fixtures.mjs';

const run = (text, pattern) => inspectChatStream(splitBytes(text, pattern));
const end = frame({ choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] }) + 'data: [DONE]\n\n';

test('eight synthetic captures have distinct, documented diagnoses', async () => {
  for (const [name, expected] of Object.entries(expectedOutcomes)) {
    assert.equal((await run(fixtures[name])).outcome, expected, name);
  }
});

test('interleaved function arguments are assembled by tool index, not arrival order', async () => {
  const result = await run(fixtures['complete-tools'], [1]);
  assert.equal(result.outcome, 'tool_calls_assembled');
  assert.deepEqual(result.tool_calls.map(({ index, id, name, arguments: args }) => ({ index, id, name, args })), [
    { index: 0, id: 'call_tokyo', name: 'get_weather', args: { city: '東京' } },
    { index: 1, id: 'call_paris', name: 'get_weather', args: { city: 'Paris' } },
  ]);
});

test('UTF-8 and LF, CRLF, or CR line endings survive single-byte boundaries', async () => {
  for (const newline of ['\n', '\r\n', '\r']) {
    const result = await run(fixtures['complete-text'].replaceAll('\n', newline), [1]);
    assert.equal(result.outcome, 'text_complete');
    assert.equal(result.content, 'Hello 東京');
  }
});

test('closed transport without observed terminal metadata is unconfirmed, not a proven server fault', async () => {
  const result = await run(fixtures['truncated-tools']);
  assert.equal(result.outcome, 'completion_unconfirmed');
  assert.equal(result.tool_calls.length, 2);
  assert.ok(result.tool_calls.every((call) => !Object.hasOwn(call, 'arguments')));
  assert.ok(result.diagnostics.every(({ severity }) => severity === 'warning'));
});

test('a finish reason without DONE remains a diagnostic warning', async () => {
  const result = await run(fixtures['terminal-without-done']);
  assert.equal(result.outcome, 'terminal_without_done');
  assert.equal(result.finish_reason, 'stop');
  assert.deepEqual(result.diagnostics, [{ code: 'missing_done_marker', severity: 'warning' }]);
});

test('choices index does not replace the index required on each tool delta', async () => {
  const result = await run(fixtures['missing-tool-index']);
  assert.equal(result.outcome, 'schema_or_input_issue');
  assert.ok(result.diagnostics.some(({ code, severity }) => code === 'missing_or_invalid_tool_index' && severity === 'error'));
  assert.equal(result.tool_calls.length, 0);
});

test('length termination is separated from transport completion', async () => {
  const result = await run(fixtures['length-limited']);
  assert.equal(result.done_seen, true);
  assert.equal(result.finish_reason, 'length');
  assert.equal(result.outcome, 'generation_truncated');
});

test('unterminated final SSE data is reported, never silently counted as a terminal event', async () => {
  const result = await run(fixtures['unterminated-event']);
  assert.equal(result.finish_reason, null);
  assert.ok(result.diagnostics.some(({ code, severity }) => code === 'unterminated_sse_event' && severity === 'warning'));
});

test('multi-line SSE data and comments follow event framing', async () => {
  const capture = ': keepalive\n\nevent: message\ndata: {"choices":\ndata: [{"index":0,"delta":{"content":"OK"},"finish_reason":null}]}\n\n' + end;
  const result = await run(capture, [1, 3, 2]);
  assert.equal(result.content, 'OK');
  assert.equal(result.outcome, 'text_complete');
});

test('malformed JSON and malformed UTF-8 cannot pass', async () => {
  assert.equal((await run('data: {bad}\n\n' + end)).outcome, 'schema_or_input_issue');
  const invalid = await inspectChatStream([new Uint8Array([0xff])]);
  assert.ok(invalid.diagnostics.some(({ code }) => code === 'read_or_utf8_error'));
});

test('valid but unsupported multi-choice input is a warning, not a claim about API correctness', async () => {
  const result = await run(frame({ choices: [{ index: 1, delta: {}, finish_reason: 'stop' }] }) + 'data: [DONE]\n\n');
  assert.equal(result.outcome, 'unsupported');
  assert.ok(result.diagnostics.some(({ code, severity }) => code === 'unsupported_choice_index' && severity === 'warning'));
});

test('1 MiB bound prevents unbounded capture processing', async () => {
  const result = await inspectChatStream([new Uint8Array(1024 * 1024 + 1)]);
  assert.ok(result.diagnostics.some(({ code }) => code === 'fixture_size_limit'));
});

test('local-file and stdin CLI work with no environment or keys and omit capture content', async () => {
  const folder = await mkdtemp(join(tmpdir(), 'sse-redaction-'));
  try {
    const path = join(folder, 'redacted.sse');
    const capture = fixtures['complete-text'].replace('Hello 東京', 'SYNTHETIC_DO_NOT_ECHO');
    await writeFile(path, capture);
    for (const [input, stdin] of [[path, undefined], ['-', capture]]) {
      const child = spawnSync(process.execPath, ['inspect-file.mjs', input], {
        cwd: import.meta.dirname, env: {}, encoding: 'utf8', input: stdin,
      });
      assert.equal(child.status, 0, child.stderr);
      const report = JSON.parse(child.stdout);
      assert.equal(report.outcome, 'text_complete');
      assert.equal(report.tool_call_count, 0);
      assert.ok(!child.stdout.includes('SYNTHETIC_DO_NOT_ECHO'));
      assert.ok(!Object.hasOwn(report, 'content'));
    }
  } finally { await rm(folder, { recursive: true, force: true }); }
});


test('partial tool arguments can end with length or content_filter without a schema mismatch', async () => {
  const partial = frame({ choices: [{ index: 0, delta: { tool_calls: [
    { index: 0, id: 'synthetic_call', type: 'function', function: { name: 'fixture', arguments: '{' } },
  ] }, finish_reason: null }] });
  for (const [reason, outcome] of [['length', 'generation_truncated'], ['content_filter', 'generation_blocked']]) {
    const result = await run(partial + frame({ choices: [{ index: 0, delta: {}, finish_reason: reason }] }) + 'data: [DONE]\n\n');
    assert.equal(result.outcome, outcome);
    assert.deepEqual(result.diagnostics, []);
    assert.ok(!Object.hasOwn(result.tool_calls[0], 'arguments'));
  }
});

test('CLI omits unknown finish-reason data and exception paths', () => {
  const secret = 'SYNTHETIC_DO_NOT_ECHO';
  const capture = frame({ choices: [{ index: 0, delta: {}, finish_reason: secret }] }) + 'data: [DONE]\n\n';
  const input = spawnSync(process.execPath, ['inspect-file.mjs', '-'], { cwd: import.meta.dirname, env: {}, encoding: 'utf8', input: capture });
  assert.equal(JSON.parse(input.stdout).finish_reason, 'unsupported_value');
  assert.ok(!input.stdout.includes(secret));
  const missing = spawnSync(process.execPath, ['inspect-file.mjs', '/not-existing-' + secret], { cwd: import.meta.dirname, env: {}, encoding: 'utf8' });
  assert.equal(missing.status, 2);
  assert.ok(!missing.stderr.includes(secret));
});


test('audio and legacy function deltas do not get a text completion verdict', async () => {
  for (const field of ['audio', 'function_call', 'refusal']) {
    const result = await run(frame({ choices: [{ index: 0, delta: { [field]: {} }, finish_reason: null }] }) + end);
    assert.equal(result.outcome, 'unsupported');
    assert.ok(result.diagnostics.some(({ code, severity }) => code === 'unsupported_' + field && severity === 'warning'));
  }
});


test('a legal final audio metadata update is unsupported, not a post-finish schema error', async () => {
  const finish = frame({ choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] });
  const audio = frame({ choices: [{ index: 0, delta: { audio: { expires_at: 0 } }, finish_reason: null }] });
  const result = await run(finish + audio + 'data: [DONE]\n\n');
  assert.equal(result.outcome, 'unsupported');
  assert.deepEqual(result.diagnostics, [{ code: 'unsupported_audio', severity: 'warning' }]);
});
