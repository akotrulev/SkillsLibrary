import { afterTest, beforeTest } from './BaseTest.js';
import { requiredEnv } from './env.js';

function androidCapabilities() {
  return {
    platformName: 'Android',
    'appium:automationName': 'UiAutomator2',
    'appium:deviceName': requiredEnv('DEVICE_NAME'),
    'appium:app': requiredEnv('APP_PATH'),
    'appium:autoGrantPermissions': true,
    'appium:settings[disableIdLocatorAutocompletion]': true,
  };
}

function iosCapabilities() {
  return {
    platformName: 'iOS',
    'appium:automationName': 'XCUITest',
    'appium:deviceName': requiredEnv('DEVICE_NAME'),
    'appium:platformVersion': requiredEnv('PLATFORM_VERSION'),
    'appium:app': requiredEnv('APP_PATH'),
    'appium:autoAcceptAlerts': true,
  };
}

function capabilitiesFor(platform: string) {
  if (platform === 'android') return androidCapabilities();
  if (platform === 'ios') return iosCapabilities();
  throw new Error(`PLATFORM must be android or ios, got ${platform}`);
}

export const config: WebdriverIO.Config = {
  runner: 'local',
  framework: 'mocha',
  specs: ['./*.spec.ts'],
  maxInstances: 1,
  capabilities: [capabilitiesFor(requiredEnv('PLATFORM'))],
  services: ['appium'],
  reporters: [['allure', { outputDir: 'allure-results', disableWebdriverScreenshotsReporting: true }]],
  outputDir: 'test-results/appium/logs',
  logLevel: 'warn',
  mochaOpts: { ui: 'bdd', timeout: 120_000 },
  beforeTest,
  afterTest,
};
