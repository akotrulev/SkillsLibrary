import { $, browser } from '@wdio/globals';
import type { ChainablePromiseElement } from 'webdriverio';

export function testIdSelector(id: string): string {
  return browser.isIOS ? `~${id}` : `id=${id}`;
}

export abstract class BasePage {
  protected byTestId(id: string): ChainablePromiseElement {
    return $(testIdSelector(id));
  }

  protected byContentDescription(description: string): ChainablePromiseElement {
    return $(`~${description}`);
  }

  protected byIosPredicate(predicate: string): ChainablePromiseElement {
    return $(`-ios predicate string:${predicate}`);
  }

  protected byIosClassChain(classChain: string): ChainablePromiseElement {
    return $(`-ios class chain:${classChain}`);
  }

  protected byAndroidUiAutomator(selector: string): ChainablePromiseElement {
    return $(`android=${selector}`);
  }

  protected byXPath(xpath: string): ChainablePromiseElement {
    return $(xpath);
  }

  abstract verifyPageLoaded(): Promise<void>;
}
