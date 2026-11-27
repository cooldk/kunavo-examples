import { inspectChatStream } from './inspect.mjs';
import { fixtures, expectedOutcomes, splitBytes } from './fixtures.mjs';

for (const [fixture, expected] of Object.entries(expectedOutcomes)) {
  const report = await inspectChatStream(splitBytes(fixtures[fixture]));
  console.log(JSON.stringify({ fixture, expected, ...report }));
  if (report.outcome !== expected) process.exitCode = 1;
}
