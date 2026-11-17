import { createHash, randomBytes } from 'node:crypto';
import { expect } from 'vitest';

const RUN_SALT = randomBytes(16).toString('hex');

export function currentTraceId(): string {
  const { testPath, currentTestName } = expect.getState();
  return createHash('sha256').update(`${RUN_SALT}|${testPath}|${currentTestName}`).digest('hex').slice(0, 32);
}

export function newTraceparent(): string {
  return `00-${currentTraceId()}-${randomBytes(8).toString('hex')}-01`;
}
