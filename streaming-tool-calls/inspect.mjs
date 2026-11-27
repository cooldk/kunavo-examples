// A small teaching checker, not a complete API/SDK implementation.
// It never calls a model, reads an environment variable, or executes a tool.
export async function inspectChatStream(chunks) {
  const decoder = new TextDecoder('utf-8', { fatal: true });
  const issues = new Set();
  const warningCodes = new Set(['missing_done_marker', 'missing_finish_reason', 'unterminated_sse_event', 'data_after_done']);
  const calls = new Map();
  let buffer = '', data = [], content = '', finishReason = null;
  let done = false, serverError = false, size = 0;
  const issue = (code) => issues.add(code);

  function event(payload) {
    if (done) { issue('data_after_done'); return; }
    if (payload === '[DONE]') { done = true; return; }
    let chunk;
    try { chunk = JSON.parse(payload); }
    catch { issue('invalid_event_json'); return; }
    if (chunk?.error) { serverError = true; issue('server_error_event'); return; }
    if (!chunk || !Array.isArray(chunk.choices)) { issue('missing_choices'); return; }
    for (const choice of chunk.choices) {
      if (choice?.index !== 0) { issue('unsupported_choice_index'); continue; }
      const delta = choice.delta ?? {};
      const unsupportedFields = ['audio', 'function_call', 'refusal'].filter((field) => delta[field] != null);
      for (const field of unsupportedFields) issue('unsupported_' + field);
      // Audio metadata may legally arrive after finish_reason; it is outside this reader.
      if (finishReason !== null) {
        if (!unsupportedFields.length) issue('choice_after_finish');
        continue;
      }
      if (delta.content != null) {
        if (typeof delta.content !== 'string') issue('unsupported_content_shape');
        else content += delta.content;
      }
      if (delta.tool_calls != null && !Array.isArray(delta.tool_calls)) {
        issue('invalid_tool_calls');
      } else for (const part of delta.tool_calls ?? []) {
        if (!Number.isInteger(part?.index) || part.index < 0) {
          issue('missing_or_invalid_tool_index');
          continue;
        }
        if (part.type != null && part.type !== 'function') {
          issue('unsupported_tool_type');
          continue;
        }
        const call = calls.get(part.index) ?? { index: part.index, id: '', name: '', arguments_text: '' };
        if (part.id != null) {
          if (typeof part.id !== 'string' || (call.id && call.id !== part.id)) issue('conflicting_tool_id');
          else call.id = part.id;
        }
        if (part.function?.name != null) {
          if (typeof part.function.name !== 'string') issue('invalid_function_name');
          else call.name += part.function.name;
        }
        if (part.function?.arguments != null) {
          if (typeof part.function.arguments !== 'string') issue('invalid_arguments_fragment');
          else call.arguments_text += part.function.arguments;
        }
        calls.set(part.index, call);
      }
      if (choice.finish_reason != null) {
        if (typeof choice.finish_reason !== 'string') issue('invalid_finish_reason');
        else finishReason = choice.finish_reason;
      }
    }
  }

  function line(value) {
    if (value === '') {
      if (data.length) event(data.join('\n'));
      data = [];
      return;
    }
    if (value.startsWith(':')) return;
    const colon = value.indexOf(':');
    const field = colon < 0 ? value : value.slice(0, colon);
    let valuePart = colon < 0 ? '' : value.slice(colon + 1);
    if (valuePart.startsWith(' ')) valuePart = valuePart.slice(1);
    if (field === 'data') data.push(valuePart);
  }

  function consume(text, final = false) {
    buffer += text;
    let end;
    while ((end = buffer.search(/[\r\n]/)) >= 0) {
      if (buffer[end] === '\r' && end === buffer.length - 1 && !final) break;
      const length = buffer[end] === '\r' && buffer[end + 1] === '\n' ? 2 : 1;
      const value = buffer.slice(0, end);
      buffer = buffer.slice(end + length);
      line(value);
    }
  }

  try {
    for await (const bytes of chunks) {
      if (!(bytes instanceof Uint8Array)) throw new TypeError('byte chunks required');
      size += bytes.byteLength;
      if (size > 1024 * 1024) { issue('fixture_size_limit'); break; }
      consume(decoder.decode(bytes, { stream: true }));
    }
    consume(decoder.decode(), true);
  } catch {
    issue('read_or_utf8_error');
  }
  // EOF is not a substitute for the blank line that dispatches an SSE event.
  if (buffer.trim() || data.length) issue('unterminated_sse_event');
  if (!done) issue('missing_done_marker');
  if (finishReason === null) issue('missing_finish_reason');

  const toolCalls = [...calls.values()].sort((a, b) => a.index - b.index);
  if (finishReason === 'tool_calls' && !toolCalls.length) issue('missing_tool_calls');
  if (toolCalls.length && finishReason && !['tool_calls', 'length', 'content_filter'].includes(finishReason)) issue('unsupported_tool_finish_combination');
  if (done && finishReason === 'tool_calls') {
    for (const call of toolCalls) {
      if (!call.id || !call.name) issue('incomplete_tool_identity');
      try { call.arguments = JSON.parse(call.arguments_text); }
      catch { issue('invalid_final_tool_json'); }
    }
  }
  let outcome;
  if (serverError) outcome = 'stream_error';
  else if ([...issues].some((code) => code.startsWith('unsupported_'))) outcome = 'unsupported';
  else if ([...issues].some((code) => !warningCodes.has(code))) outcome = 'schema_or_input_issue';
  else if (finishReason === null) outcome = 'completion_unconfirmed';
  else if (!done || issues.has('unterminated_sse_event')) outcome = 'terminal_without_done';
  else if (finishReason === 'length') outcome = 'generation_truncated';
  else if (finishReason === 'content_filter') outcome = 'generation_blocked';
  else if (finishReason === 'tool_calls') outcome = 'tool_calls_assembled';
  else if (finishReason === 'stop') outcome = 'text_complete';
  else { outcome = 'unsupported'; issue('unsupported_finish_reason'); }
  // Parsed arguments are never made available as executable-ready on failure.
  if (outcome !== 'tool_calls_assembled') for (const call of toolCalls) delete call.arguments;
  return { outcome, done_seen: done, finish_reason: finishReason, content, tool_calls: toolCalls,
    diagnostics: [...issues].map((code) => ({ code, severity: warningCodes.has(code) || code.startsWith('unsupported_') ? 'warning' : 'error' })) };
}
