# Single-file report — one HTML file for an artifact or an attachment

A normal Allure report is a folder (`index.html` plus `data/`, `widgets/`, `plugins/`) that must be served over HTTP: opened from disk, the browser blocks its data requests and the page stays empty. A **single-file** report inlines everything into one `index.html` that opens from disk, from a CI artifact download, or as an e-mail or ticket attachment.

Verified 2026-11-17 in the pinned generator itself: `allure-commandline` 2.46.1's `generate` command declares `--single-file` ("Generate Allure report in single file mode."), `-c` / `--clean` and `-o` / `--report-dir` / `--output`. Allure Report 2's documentation (*View report*) describes the same option.

## Command

```bash
allure generate --clean --single-file -o allure-report build/allure-results
```

- The output is `allure-report/index.html`, one file. Keep the folder name: `--clean` empties the output folder first, so it is never a mount point or the workspace root.
- The CLI is the one pin, `allure-commandline` 2.46.1, wherever it runs: `npm i -g allure-commandline@2.46.1` on a runner, the checksummed Maven Central archive in an image (`qa/cicd/java/skills/ci-pipelines/references/fat-jar-and-container.md`), `allure.version` in Gradle. Never an unversioned `npm i -g allure-commandline` or a package-manager `allure`.
- Gradle: `./gradlew allureReport --single-file=true` for one run, or `singleFile = true` under `allure { report { } }` (the allure-gradle README); the plugin runs the same pinned generator.

## When to use which

| Report | Use for |
|---|---|
| Single file | A PR or nightly artifact someone downloads and opens; a report attached to a defect or sent by mail; the container run's output |
| Folder | The published site (GitHub Pages, GitLab Pages, an Azure static page) with history and trends |

- History works the same way: copy the previous report's `history/` into the results folder before `generate`. Carry history forward from the published folder report, whose `history/` folder is what the next run copies; generate the single file from the same results as a second output when both are wanted.
- A single file grows with every attachment it inlines. Playwright traces and videos make it large: keep them as separate artifacts (`build/playwright-artifacts/`) when the file must travel by mail.
- The Playwright trace viewer link inside the report still needs internet access, as in the folder report.
