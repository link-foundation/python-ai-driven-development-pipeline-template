While checking the latest `@actions/artifact@6.3.1` on Node 26.13.1, I reproduced a recognized transient network error bypassing the configured Twirp retry budget. I searched existing network/retry/FinalizeArtifact reports, including #2575 (a different download-response cleanup bug), and found no report for this branch.

In `ArtifactHttpClient.retryableRequest`, the catch block immediately throws `new NetworkError(error.code)` for ECONNRESET, ENOTFOUND, ETIMEDOUT, ECONNREFUSED and EHOSTUNREACH. Therefore `maxAttempts: 3` does not retry even one simulated ECONNRESET followed by success. The outer `request` wrapper then discards the structured code/cause, making callers parse the error message to recognize the transient failure.

Reproduce without any real network access, credentials or waiting after installing `@actions/artifact@6.3.1` and `@actions/http-client@4.0.1`:

```js
import assert from 'node:assert/strict';
import { HttpClient } from '@actions/http-client';
// Relative path is intentional: this is a diagnostic of the published internal transport.
import { internalArtifactTwirpClient } from './node_modules/@actions/artifact/lib/internal/shared/artifact-twirp-client.js';

process.env.ACTIONS_RUNTIME_TOKEN = 'example-runtime-token';
process.env.ACTIONS_RESULTS_URL = 'https://example.invalid';
let calls = 0;
HttpClient.prototype.post = async () => {
  calls++;
  if (calls === 1) throw Object.assign(new Error('mock reset'), { code: 'ECONNRESET' });
  return { message: { statusCode: 200, headers: {} }, readBody: async () => JSON.stringify({ ok: true }) };
};
const client = internalArtifactTwirpClient({ maxAttempts: 3, retryIntervalMs: 1 });
await assert.rejects(client.CreateArtifact({ workflowRunBackendId: '1', workflowJobRunBackendId: '2', name: 'evidence', version: 7 }), /ECONNRESET/);
assert.equal(calls, 1);
```

Could retryable network failures participate in the existing bounded policy, with structured code/cause retained? Keep permanent 4xx and quota errors immediate. For state-changing calls, please also document/support safe lost-response handling: a finalized upload may exist when its response was lost, so blindly restarting the entire upload can cause an existing-name conflict. An SDK-supported operation-level policy would let consumers avoid duplicating that recovery logic.

Our retained consumer workaround in https://github.com/link-foundation/python-ai-driven-development-pipeline-template/pull/152 bounds retries at the artifact transport boundary, without repeating the test/build producer. Names must be unique per producer; it rejects artifacts present before the first attempt, and only reconciles/replaces that producer's unique name on a retry. Existing mocked tests cover transient codes, permanent failures, bounded exhaustion, lost finalize responses, preexisting-artifact refusal, download digest validation and strict extraction. The checked-in experiment additionally exercises this actual published SDK branch, rather than only a mock of our own adapter.
