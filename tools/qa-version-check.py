#!/usr/bin/env python3
"""Checks that every version pin under qa/ matches the one the library teaches.

Run from the repo root: python3 tools/qa-version-check.py
Prints `OK` and exits 0, or one `file:line found X expected Y` per mismatch and exits 1.

Stack of a file: qa/<stack>/, qa/reporting/<stack>/ and qa/cicd/<stack>/ belong to that stack;
qa/_shared/python-web-testing/ is `python`; qa/_shared/webmcp-testing/ takes its stack from the
file name or extension. Any other _shared file is skipped unless it carries a pin, which is reported.
A leading ^ or ~ is stripped before comparing.

Bumping Java and .NET to Playwright 1.64 once Maven and NuGet publish it:
1. Change EXPECTED in this file.
2. Run the checker. It lists every site to change.
3. Change those sites.
4. Replace each "from 1.64" line with the native API.
5. Delete the matching row from the version-lane table of the plan that does the bump.
"""
import os
import re
import sys

EXPECTED = {
    "typescript": {"playwright": "1.64.0", "webdriverio": "10.0.2", "appium": "3.8.0"},
    "java": {"playwright": "1.63.0", "java-client": "11.0.0", "allure-testng": "3.0.0"},
    "dotnet": {"playwright": "1.63.0", "appium-webdriver": "9.0.0"},
    "python": {"playwright": "1.63.0"},
}
STACKS = ("typescript", "java", "dotnet")
TEXT_SUFFIXES = (".md", ".json", ".ts", ".java", ".cs", ".csproj", ".props", ".kts", ".gradle",
                 ".xml", ".yml", ".yaml", ".txt", ".toml", ".sh", ".py", ".runsettings")
V = r"[\^~]?(\d+(?:\.\d+)+)"

PINS = [
    ("playwright", r'"@playwright/test"\s*:\s*"' + V + '"'),
    ("playwright", r"@playwright/test@" + V),
    ("playwright", r'"playwright"\s*:\s*"' + V + '"'),
    ("playwright", r"com\.microsoft\.playwright:playwright:" + V),
    ("playwright", r"<artifactId>playwright</artifactId>\s*<version>" + V + "</version>"),
    ("playwright", r'Microsoft\.Playwright[\w.]*"\s+Version="' + V + '"'),
    ("playwright", r'PackageVersion\s+Include="Microsoft\.Playwright[\w.]*"\s+Version="' + V + '"'),
    ("playwright", r"(?<![\w-])playwright==" + V),
    ("playwright", r"mcr\.microsoft\.com/playwright(?:/java|/dotnet|/python)?:v" + V + r"-[a-z]+"),
    ("webdriverio", r'"webdriverio"\s*:\s*"' + V + '"'),
    ("appium", r'"appium"\s*:\s*"' + V + '"'),
    ("java-client", r"io\.appium:java-client:" + V),
    ("java-client", r"<artifactId>java-client</artifactId>\s*<version>" + V + "</version>"),
    ("allure-testng", r"io\.qameta\.allure:allure-testng:" + V),
    ("allure-testng", r"<artifactId>allure-testng</artifactId>\s*<version>" + V + "</version>"),
    ("appium-webdriver", r'Appium\.WebDriver"\s+Version="' + V + '"'),
]


def stack_of(path):
    parts = path.split("/")
    if parts[1] in STACKS:
        return parts[1]
    if parts[1] in ("reporting", "cicd") and parts[2] in STACKS:
        return parts[2]
    if parts[1] == "_shared" and parts[2] == "python-web-testing":
        return "python"
    if parts[1] == "_shared" and parts[2] == "webmcp-testing":
        name = parts[-1]
        for stack, marks in (("typescript", ("typescript", ".ts")), ("java", ("java",)),
                             ("dotnet", ("dotnet", ".cs", ".runsettings"))):
            if any(mark in name for mark in marks):
                return stack
        return None
    return None


def check_file(path, findings):
    stack = stack_of(path)
    text = open(path, errors="ignore").read()
    for key, pattern in PINS:
        for m in re.finditer(pattern, text, re.S):
            line = text.count("\n", 0, m.start(1)) + 1
            found = m.group(1)
            if stack is None:
                findings.append(f"{path}:{line} pin {key} {found} in a file with no stack")
                continue
            expected = EXPECTED[stack].get(key)
            if expected is not None and found != expected:
                findings.append(f"{path}:{line} found {key} {found} expected {expected}")


def main():
    findings = []
    for root, _, files in os.walk("qa"):
        for name in sorted(files):
            if name.endswith(TEXT_SUFFIXES) and name != "package-lock.json":
                check_file(os.path.join(root, name), findings)
    print("\n".join(findings) or "OK")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
