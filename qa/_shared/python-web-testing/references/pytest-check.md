# From a script to a check (pytest-playwright 0.10.0)

When the same verification will be run again, make it a pytest file and let the plugin keep the evidence:

```ini
[pytest]
addopts = --tracing=retain-on-failure --video=retain-on-failure --screenshot=only-on-failure --full-page-screenshot --output=test-results
```

- `--tracing` and `--video` take only `on`, `off` or `retain-on-failure` in 0.10.0; `--screenshot` takes `on`,
  `off` or `only-on-failure`. Kept files land under `test-results/` per test.
- Open a kept trace with `playwright show-trace test-results/<test>/trace.zip`, or drop it on
  https://trace.playwright.dev, which loads it in the browser without uploading it.
