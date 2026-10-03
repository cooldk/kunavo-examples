import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';

function run(file, args, env) {
  return new Promise((resolve, reject) => {
    const p = spawn(process.execPath, [file, ...args], { env: { ...process.env, ...env } });
    let out = '', err = '';
    p.stdout.on('data', b => out += b);
    p.stderr.on('data', b => err += b);
    p.on('error', reject);
    p.on('close', code => resolve({ code, out, err }));
  });
}

test('migration CLI maps the first positional model without --request', async () => {
  const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ data: [{ id: 'claude-sonnet-4-6' }, { id: 'gpt-5-5' }] }));
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  try {
    const result = await run('migrate-from-openrouter/migrate.mjs', ['anthropic/claude-sonnet-4.6', 'openai/gpt-5.5'], {
      KUNAVO_API_KEY: 'fixture-key', KUNAVO_BASE_URL: `http://127.0.0.1:${server.address().port}/v1`
    });
    assert.equal(result.code, 0, result.err);
    assert.match(result.out, /anthropic\/claude-sonnet-4\.6\s+-> claude-sonnet-4-6/);
    assert.match(result.out, /openai\/gpt-5\.5\s+-> gpt-5-5/);
  } finally { await new Promise(r => server.close(r)); }
});

test('extraction workflow rejects non-objects before marking them valid', () => {
  const workflow = JSON.parse(readFileSync('n8n-templates/01-extract-and-validate.json', 'utf8'));
  const validators = workflow.nodes.filter(n => n.name === 'Validate' || n.name === 'Validate retry');
  assert.equal(validators.length, 2);
  const valid = { name: 'Dana', email: 'dana@example.com', company: null, intent: 'support', summary: 'Please help.' };
  for (const node of validators) {
    const check = raw => new Function('$input', '$', node.parameters.jsCode)(
      { all: () => [{ json: { text: raw } }] }, () => ({ first: () => ({ json: { Text: 'Source' } }) })
    )[0].json;
    for (const raw of ['null', '[]', '42', '"hello"', 'broken']) assert.equal(check(raw).valid, false, raw);
    assert.equal(check(JSON.stringify(valid)).valid, true);
    assert.equal(check(JSON.stringify({ ...valid, email: 'invalid' })).valid, false);
    assert.equal(check(JSON.stringify({ ...valid, email: null, name: null })).valid, false);
  }
});
