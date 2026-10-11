import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import allureReporter from '@wdio/allure-reporter';
import { browser } from '@wdio/globals';
import logger from '@wdio/logger';
import type { Frameworks } from '@wdio/types';

const log = logger('evidence');
const EVIDENCE_ROOT = join('test-results', 'appium');
const RECORDING_SECONDS = 180;
const LOG_TAIL_LINES = 200;
const recordLocally = process.env.DEVICE_FARM === undefined;

function folderName(title: string): string {
  return title.replace(/[^A-Za-z0-9._-]+/g, '_');
}

async function tolerate<T>(what: string, capture: () => Promise<T>): Promise<T | undefined> {
  try {
    return await capture();
  } catch (error) {
    if (!(error instanceof Error)) throw error;
    log.warn('Could not capture %s: %s', what, error.message);
    return undefined;
  }
}

async function keep(folder: string, name: string, extension: string, type: string, content: Buffer | string): Promise<void> {
  await mkdir(folder, { recursive: true });
  await writeFile(join(folder, `${name}.${extension}`), content);
  allureReporter.addAttachment(name, content, type);
}

async function deviceLogTail(logType: string): Promise<string> {
  const entries = await browser.getLogs(logType);
  return entries.slice(-LOG_TAIL_LINES).map((entry) => JSON.stringify(entry)).join('\n');
}

export async function beforeTest(): Promise<void> {
  if (!recordLocally) return;
  await tolerate('recording start', () => browser.startRecordingScreen({ timeLimit: RECORDING_SECONDS, forceRestart: true }));
}

export async function afterTest(test: Frameworks.Test, _context: unknown, result: Frameworks.TestResult): Promise<void> {
  const recording = recordLocally ? await tolerate('recording stop', () => browser.stopRecordingScreen()) : undefined;
  if (result.passed) return;

  const folder = join(EVIDENCE_ROOT, folderName(test.fullTitle));
  const logType = browser.isAndroid ? 'logcat' : 'syslog';
  await tolerate('screenshot', async () =>
    keep(folder, 'screenshot', 'png', 'image/png', Buffer.from(await browser.takeScreenshot(), 'base64')));
  await tolerate('page source', async () =>
    keep(folder, 'page-source', 'xml', 'application/xml', await browser.getPageSource()));
  await tolerate(logType, async () => keep(folder, logType, 'log', 'text/plain', await deviceLogTail(logType)));
  if (recording) {
    await tolerate('recording', () => keep(folder, 'recording', 'mp4', 'video/mp4', Buffer.from(recording, 'base64')));
  }
}
