import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { inspectChatStream } from './inspect.mjs';

// Local file or stdin only. No network, credentials, remote URL, or telemetry.
const path = process.argv[2];
if (!path || process.argv.length !== 3) {
  console.error('Usage: node inspect-file.mjs <local-redacted.sse | ->');
  process.exitCode = 2;
} else {
  try {
    if (path !== '-') {
      const info = await stat(path);
      if (!info.isFile() || info.size > 1024 * 1024) throw new Error('input limit');
    }
    const result = await inspectChatStream(path === '-' ? process.stdin : createReadStream(path));
    // Deliberately omit text, tool arguments, call IDs, and function names.
    console.log(JSON.stringify({ outcome: result.outcome, done_seen: result.done_seen,
      finish_reason: result.finish_reason === null || ['stop', 'length', 'content_filter', 'tool_calls', 'function_call'].includes(result.finish_reason) ? result.finish_reason : 'unsupported_value', tool_call_count: result.tool_calls.length,
      diagnostics: result.diagnostics }, null, 2));
  } catch {
    console.error('Could not read a local regular file within the 1 MiB limit.');
    process.exitCode = 2;
  }
}
