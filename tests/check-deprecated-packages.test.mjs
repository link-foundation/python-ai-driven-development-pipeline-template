import assert from 'node:assert/strict';
import { test } from 'node:test';

import { checkDeprecations, collectRegistryPackages } from '../scripts/check-deprecated-packages.mjs';

const lock = {
  packages: {
    '': { version: '1.0.0' },
    'node_modules/example': {
      version: '1.0.0',
      resolved: 'https://registry.npmjs.org/example/-/example-1.0.0.tgz',
    },
    'node_modules/example/node_modules/alias': { name: '@scope/scanner', version: '2.0.0' },
    'node_modules/workspace': { link: true },
    'node_modules/local': { version: '1.0.0', resolved: 'file:local.tgz' },
    'node_modules/git': { version: '1.0.0', resolved: 'git+https://example.org/repo.git' },
  },
};
const packages = collectRegistryPackages([['first lock', lock], ['second lock', lock]]);

test('inventories registry versions, including aliases, and deduplicates across locks', () => {
  assert.deepEqual(packages.map(({ name, version, paths }) => [name, version, [...paths]]), [
    ['example', '1.0.0', ['first lock', 'second lock']],
    ['@scope/scanner', '2.0.0', ['first lock', 'second lock']],
  ]);
  assert.throws(() => collectRegistryPackages([['bad-lock', {}]]), /no npm packages map/);
});

for (const strict of [false, true]) {
  test(`live deprecation is reported with scheduled enforcement=${strict}`, async () => {
    const messages = [];
    const urls = [];
    const code = await checkDeprecations(packages, {
      strict,
      log: (message) => messages.push(message),
      fetchVersion: async (url) => {
        urls.push(url.href);
        return Response.json(url.pathname.includes('example')
          ? { name: 'example', version: '1.0.0', deprecated: 'Use another package.\nThanks!' }
          : { name: '@scope/scanner', version: '2.0.0' });
      },
    });
    assert.equal(code, strict ? 1 : 0);
    assert.ok(urls.includes('https://registry.npmjs.org/%40scope%2Fscanner/2.0.0'));
    assert.ok(messages.some((line) => line.startsWith(strict ? '::error::' : '::warning::')
      && line.includes('example@1.0.0') && line.includes('%0A')));
    assert.match(messages.at(-1), /2 checked, 1 deprecated, 0 unanswered/);
  });
}

test('missing, malformed and repeatedly unavailable responses fail in report mode', async () => {
  const messages = [];
  let requests = 0;
  const missing = checkDeprecations(packages, {
    log: (message) => messages.push(message),
    fetchVersion: async (url) => {
      if (url.pathname.includes('example')) return new Response(null, { status: 404 });
      requests += 1;
      return new Response(null, { status: 503 });
    },
  });
  assert.equal(await missing, 1);
  assert.equal(requests, 3);
  assert.match(messages.at(-1), /2 unanswered/);
  assert.equal(await checkDeprecations(packages, {
    log() {},
    fetchVersion: async () => Response.json({ name: 'wrong', version: '0.0.0' }),
  }), 1);
});
