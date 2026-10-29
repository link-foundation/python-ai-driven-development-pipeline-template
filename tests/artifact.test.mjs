import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { test } from 'node:test';
import { isTransient, uploadWithRetry, downloadWithRetry } from '../.github/actions/artifact/transport.mjs';
import { findFiles, packagePages } from '../.github/actions/artifact/files.mjs';

const network = (code = 'ENOTFOUND') => Object.assign(new Error(`Unable to make request: ${code}`), { code });
const notFound = () => Object.assign(new Error('not found'), { name: 'ArtifactNotFoundError' });
const noWait = { sleep: async () => {}, log: () => {} };

for (const code of ['ENOTFOUND', 'EAI_AGAIN', 'ECONNRESET', 'ETIMEDOUT', 'ECONNREFUSED', 'EHOSTUNREACH', 'EPIPE']) {
  test(`recovers ${code} without rerunning the producer`, async () => {
    let uploads = 0;
    let deletes = 0;
    const client = {
      getArtifact: async () => { throw notFound(); },
      deleteArtifact: async () => { deletes++; throw notFound(); },
      uploadArtifact: async () => { if (++uploads === 1) throw network(code); return { id: 42 }; },
    };
    const result = await uploadWithRetry(client, 'evidence', ['file'], '/root', {}, noWait);
    assert.equal(result.id, 42);
    assert.equal(uploads, 2);
    assert.equal(deletes, 1);
  });
}

test('replaces only its own artifact after a lost finalize response', async () => {
  let finalized = false;
  let uploads = 0;
  const client = {
    getArtifact: async () => { throw notFound(); },
    deleteArtifact: async () => { assert.equal(finalized, true); finalized = false; },
    uploadArtifact: async () => {
      assert.equal(finalized, false, 'duplicate-name conflict');
      finalized = true;
      if (++uploads === 1) throw network('ECONNRESET');
      return { id: 43 };
    },
  };
  assert.equal((await uploadWithRetry(client, 'site', ['file'], '/root', {}, noWait)).id, 43);
});

test('never replaces a preexisting artifact', async () => {
  const client = { getArtifact: async () => ({ artifact: { id: 99 } }) };
  await assert.rejects(uploadWithRetry(client, 'stale', ['file'], '/root', {}, noWait), /already exists/);
});

test('transport exhaustion fails after exactly three uploads', async () => {
  let calls = 0;
  const client = {
    getArtifact: async () => { throw notFound(); },
    deleteArtifact: async () => { throw notFound(); },
    uploadArtifact: async () => { calls++; throw network(); },
  };
  await assert.rejects(uploadWithRetry(client, 'site', ['file'], '/root', {}, noWait), /ENOTFOUND/);
  assert.equal(calls, 3);
});

for (const error of [Object.assign(network(), { status: 403 }), new Error('Artifact storage quota has been hit'), new Error('Failed to CreateArtifact: 409 Conflict'), new Error('401 Unauthorized'), new Error('No files were found')]) {
  test(`permanent refusal is immediate: ${error.message}`, async () => {
    assert.equal(isTransient(error), false);
    let calls = 0;
    const client = {
      getArtifact: async () => { throw notFound(); },
      uploadArtifact: async () => { calls++; throw error; },
    };
    await assert.rejects(uploadWithRetry(client, 'site', ['file'], '/root', {}, noWait));
    assert.equal(calls, 1);
  });
}

test('nested transport errors retry but permanent statuses dominate', () => {
  assert.equal(isTransient(new Error('wrapper', { cause: network() })), true);
  assert.equal(isTransient(Object.assign(new Error('503 unavailable'), { status: 503 })), true);
  assert.equal(isTransient(Object.assign(new Error('429 rate limited'), { status: 429 })), true);
  assert.equal(isTransient(new Error('wrapper', { cause: Object.assign(network(), { status: 401 }) })), false);
});

test('empty and missing evidence fails before network access; globs preserve root', async (t) => {
  const root = await mkdtemp(path.join(tmpdir(), 'artifact-test-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await assert.rejects(findFiles(root), /empty|No files/);
  await assert.rejects(findFiles(path.join(root, 'missing')), /empty|No files/);
  await mkdir(path.join(root, 'nested'));
  await writeFile(path.join(root, 'nested', 'bytes.bin'), Buffer.from([0, 255, 42]));
  await writeFile(path.join(root, '.secret'), 'excluded');
  const evidence = await findFiles(root);
  assert.equal(evidence.files.length, 1);
  assert.equal(evidence.root, root);
  assert.equal((await findFiles(path.join(root, 'nested', '*'))).root, path.join(root, 'nested'));
});

test('Pages artifact contains artifact.tar and the complete visible site', async (t) => {
  const root = await mkdtemp(path.join(tmpdir(), 'pages-test-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await writeFile(path.join(root, 'index.html'), 'site');
  const archive = await packagePages(root);
  t.after(archive.cleanup);
  assert.equal(path.basename(archive.file), 'artifact.tar');
  assert.match(execFileSync('tar', ['-tf', archive.file], { encoding: 'utf8' }), /index.html/);
  assert.equal(execFileSync('tar', ['-xOf', archive.file, './index.html'], { encoding: 'utf8' }), 'site');
});

test('download retries transport, skips deprecated extraction and enforces digest', async (t) => {
  const root = await mkdtemp(path.join(tmpdir(), 'download-test-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  let calls = 0;
  let extracts = 0;
  const client = { downloadArtifact: async (id, options) => {
    assert.equal(options.skipDecompress, true);
    assert.equal(options.expectedHash, `sha256:${'a'.repeat(64)}`);
    if (++calls === 1) throw network();
    await writeFile(path.join(options.path, 'archive.zip'), 'bytes');
    return { digestMismatch: false };
  } };
  await downloadWithRetry(client, { id: 1, name: 'dist', digest: `sha256:${'a'.repeat(64)}` }, root, {
    ...noWait,
    extract: async (archive, destination) => {
      assert.equal(await readFile(archive, 'utf8'), 'bytes');
      assert.equal(destination, root);
      extracts++;
    },
  });
  assert.equal(calls, 2);
  assert.equal(extracts, 1);
  await assert.rejects(downloadWithRetry({ downloadArtifact: async () => ({ digestMismatch: true }) }, { id: 1, digest: `sha256:${'a'.repeat(64)}` }, root, noWait), /digest/i);
  await assert.rejects(downloadWithRetry(client, { id: 1 }, root, noWait), /digest/i);
});
