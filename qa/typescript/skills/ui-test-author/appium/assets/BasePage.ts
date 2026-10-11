import { $, browser } from '@wdio/globals';
import type { ChainablePromiseElement } from 'webdriverio';

export function testIdSelector(id: string): string {
  return browser.isIOS ? `~${id}` : `id=${id}`;
}

export abstract class BasePage {
  private static readonly TIMEOUT_MS = 10_000;
  private static readonly NOT_DISPLAYED = 'element not displayed within the timeout';

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

  protected async isElementVisible(element: ChainablePromiseElement): Promise<boolean> {
    try {
      await browser.waitUntil(() => element.isDisplayed(), {
        timeout: BasePage.TIMEOUT_MS,
        timeoutMsg: BasePage.NOT_DISPLAYED,
      });
      return true;
    } catch (error) {
      if (error instanceof Error && error.message === BasePage.NOT_DISPLAYED) return false;
      throw error;
    }
  }

  abstract verifyPageLoaded(): Promise<void>;
}
