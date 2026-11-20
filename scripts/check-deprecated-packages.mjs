#!/usr/bin/env node
// Check live npm metadata because a lockfile captures deprecation only at resolution time.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';

const registry = new URL('https://registry.npmjs.org/');
const maxAttempts = 3;
const requestTimeoutMs = 8_000;
const concurrency = 16;

export function collectRegistryPackages(locks) {
  const packages = new Map();
  for (const [path, lock] of locks) {
    if (!lock.packages || typeof lock.packages !== 'object' || Array.isArray(lock.packages)) {
      throw new Error(`${path} has no npm packages map`);
    }
    for (const [location, info] of Object.entries(lock.packages)) {
      if (!/(?:^|\/)node_modules\//.test(location) || info.link || info.inBundle) continue;
      const inferredName = location.split(/(?:^|\/)node_modules\//).at(-1);
      const { name = inferredName, version, resolved } = info;
      if (resolved && !resolved.startsWith(registry.href)) continue;
      if (typeof version !== 'string' || !version) {
        throw new Error(`${path}: missing version for ${location}`);
      }
      const key = `${name}@${version}`;
      const entry = packages.get(key) ?? { name, version, paths: new Set() };
      entry.paths.add(path);
      packages.set(key, entry);
    }
  }
  return [...packages.values()];
}

async function readVersion({ name, version }, fetchVersion) {
  const url = new URL(`${encodeURIComponent(name)}/${encodeURIComponent(version)}`, registry);
  for (let attempt = 1; ; attempt += 1) {
    try {
      const response = await fetchVersion(url, {
        headers: { accept: 'application/json' },
        signal: AbortSignal.timeout(requestTimeoutMs),
      });
      if (response.status === 404) return { error: 'version was not found (404)' };
      if (!response.ok) throw new Error(`registry returned HTTP ${response.status}`);
      const manifest = await response.json();
      if (manifest?.name !== name || manifest?.version !== version) {
        return { error: 'registry returned a different package or version' };
      }
      if ('deprecated' in manifest && typeof manifest.deprecated !== 'string') {
        return { error: 'registry returned an invalid deprecation field' };
      }
      return { deprecated: manifest.deprecated };
    } catch (error) {
      if (attempt >= maxAttempts) return { error: error.message };
      await delay(attempt * 250);
    }
  }
}

function annotation(level, message, log) {
  const escaped = message.replaceAll('%', '%25').replaceAll('\r', '%0D').replaceAll('\n', '%0A');
  log(`::${level}::${escaped}`);
}

export async function checkDeprecations(
  packages,
  { strict = false, fetchVersion = fetch, log = console.log } = {},
) {
  let next = 0;
  let deprecated = 0;
  let unanswered = 0;
  const workers = Array.from({ length: Math.min(concurrency, packages.length) }, async () => {
    while (next < packages.length) {
      const entry = packages[next++];
      const result = await readVersion(entry, fetchVersion);
      const label = `${entry.name}@${entry.version} (${[...entry.paths].join(', ')})`;
      if ('error' in result) {
        unanswered += 1;
        annotation('error', `${label}: ${result.error}`, log);
      } else if (result.deprecated) {
        deprecated += 1;
        annotation(strict ? 'error' : 'warning', `${label}: ${result.deprecated}`, log);
      }
    }
  });
  await Promise.all(workers);
  log(`npm registry: ${packages.length} checked, ${deprecated} deprecated, ${unanswered} unanswered.`);
  return unanswered > 0 || (strict && deprecated > 0) ? 1 : 0;
}

async function main() {
  const inventory = fileURLToPath(new URL('./audit-npm-locks.sh', import.meta.url));
  const locks = execFileSync('bash', [inventory, '--list0'], { encoding: 'utf8' })
    .split('\0')
    .filter(Boolean)
    .map((path) => [path, JSON.parse(readFileSync(path, 'utf8'))]);
  return checkDeprecations(collectRegistryPackages(locks), {
    strict: process.env.DEPRECATED_FAIL === 'true',
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    process.exitCode = await main();
  } catch (error) {
    annotation('error', `Could not check npm deprecations: ${error.message}`, console.error);
    process.exitCode = 1;
  }
}
