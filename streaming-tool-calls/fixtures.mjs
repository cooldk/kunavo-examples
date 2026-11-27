// Every value is synthetic. These are not captured customer/provider responses.
const chunk = (delta, finish_reason = null) => ({
  id: 'synthetic-chat', object: 'chat.completion.chunk', created: 0,
  model: 'fixture-model', choices: [{ index: 0, delta, finish_reason }],
});
export const frame = (value) => `data: ${JSON.stringify(value)}\n\n`;
const done = 'data: [DONE]\n\n';
const initialTools = chunk({ tool_calls: [
  { index: 0, id: 'call_tokyo', type: 'function', function: { name: 'get_weather', arguments: '{"city":"' } },
  { index: 1, id: 'call_paris', type: 'function', function: { name: 'get_weather', arguments: '{"city":"Pa' } },
] });
const toolTail = chunk({ tool_calls: [
  { index: 1, function: { arguments: 'ris"}' } },
  { index: 0, function: { arguments: '東京"}' } },
] });
export const fixtures = {
  'complete-tools': frame(initialTools) + frame(toolTail) + frame(chunk({}, 'tool_calls')) + done,
  'missing-tool-index': frame(chunk({ tool_calls: [
    { id: 'call_synthetic', type: 'function', function: { name: 'get_weather', arguments: '{"city":"Paris"}' } },
  ] })) + frame(chunk({}, 'tool_calls')) + done,
  'truncated-tools': frame(initialTools) + frame(toolTail),
  'length-limited': frame(chunk({ content: 'Partial answer' })) + frame(chunk({}, 'length')) + done,
  'unterminated-event': frame(chunk({ content: 'Visible text' })) + `data: ${JSON.stringify(chunk({}, 'stop'))}`,
  'midstream-error': frame(chunk({ content: 'Partial answer' })) + frame({ error: { type: 'synthetic_error', message: 'Fixture only' } }),
  'complete-text': ': synthetic keepalive\n\n' + frame(chunk({ content: 'Hello 東京' })) + frame(chunk({}, 'stop')) + done,
  'terminal-without-done': frame(chunk({ content: 'Hello' })) + frame(chunk({}, 'stop')),
};
export const expectedOutcomes = {
  'complete-tools': 'tool_calls_assembled',
  'missing-tool-index': 'schema_or_input_issue',
  'truncated-tools': 'completion_unconfirmed',
  'length-limited': 'generation_truncated',
  'unterminated-event': 'completion_unconfirmed',
  'midstream-error': 'stream_error',
  'complete-text': 'text_complete',
  'terminal-without-done': 'terminal_without_done',
};
export function* splitBytes(text, pattern = [1, 2, 7, 13, 3, 5]) {
  const bytes = new TextEncoder().encode(text);
  for (let offset = 0, step = 0; offset < bytes.length; step++) {
    const size = pattern[step % pattern.length];
    yield bytes.subarray(offset, offset + size);
    offset += size;
  }
}
