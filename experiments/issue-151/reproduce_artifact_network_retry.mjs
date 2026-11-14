// No network, credentials or waits: invoke the published SDK with a fake HTTP transport.
import assert from 'node:assert/strict';
import { HttpClient } from '../../.github/actions/artifact/node_modules/@actions/http-client/lib/index.js';
import { internalArtifactTwirpClient } from '../../.github/actions/artifact/node_modules/@actions/artifact/lib/internal/shared/artifact-twirp-client.js';

process.env.ACTIONS_RUNTIME_TOKEN = 'example-runtime-token';
process.env.ACTIONS_RESULTS_URL = 'https://example.invalid';
const originalPost = HttpClient.prototype.post;
let calls = 0;
HttpClient.prototype.post = async () => {
  calls++;
  if (calls === 1) throw Object.assign(new Error('mock connection reset'), { code: 'ECONNRESET' });
  return { message: { statusCode: 200, headers: {} }, readBody: async () => JSON.stringify({ ok: true }) };
};
try {
  const client = internalArtifactTwirpClient({ maxAttempts: 3, retryIntervalMs: 1 });
  await assert.rejects(client.CreateArtifact({ workflowRunBackendId: '1', workflowJobRunBackendId: '2', name: 'unique-producer-evidence', version: 4 }), /ECONNRESET/);
  assert.equal(calls, 1, 'the current SDK refuses a recognized network error without retrying');
  console.log('SDK 6.3.1: ECONNRESET fails after 1 call despite maxAttempts=3; no real HTTP used.');
} finally {
  HttpClient.prototype.post = originalPost;
}
