# Deep-dive details — `qa-typescript:device-cloud`

Sections kept out of SKILL.md for on-demand loading. Read what the task needs.

## Agent tooling on the farm

### BrowserStack MCP — triage a red farm run

BrowserStack's MCP server lets an agent read the cloud's own evidence for a red run. Register it:

```bash
claude mcp add --scope user --transport http browserstack https://mcp.browserstack.com/mcp
```

Then `/mcp` in a session signs in with OAuth, so no username or access key lands in any config. The remote
server has no Local Testing: it cannot reach `localhost`, a VPN or a firewalled staging host, and it disables
the tools that need local files (`runPercyScan`, `addPercySnapshotCommands`, …). Where those are needed, run
the package locally from a project `.mcp.json` that takes the keys from the environment (Claude Code expands
`${VAR}` there, so the committed file holds only the placeholders):

```json
{
  "mcpServers": {
    "browserstack": {
      "command": "npx",
      "args": ["-y", "@browserstack/mcp-server@2.6.8"],
      "env": {
        "BROWSERSTACK_USERNAME": "${BROWSERSTACK_USERNAME}",
        "BROWSERSTACK_ACCESS_KEY": "${BROWSERSTACK_ACCESS_KEY}"
      }
    }
  }
}
```

The version is pinned for the same reason as the Playwright and Appium servers: the agents name its tools
in `tools:`. They are granted the triage and scan tools by name, never the five core catalog tools
(`listProducts`, `describeEntity`, `searchCapability`, `describeCapability`, `invokeCapability`), which reach
every write the account allows.

| Need | Tool |
|---|---|
| The build's tests, and which failed | `listTestIds` (status `failed`), `listSessions` |
| One session's logs (App Automate needs the hashed build id; it is resolved from the session) | `getFailureLogs` |
| The screenshots the farm took | `fetchAutomationScreenshots` |
| Build details and the quality-gate result | `fetchBuildInsights` |
| AI root-cause analysis | `fetchRCA` (numeric test id) |

- `fetchRCA` **proposes**. A fix lands in the screen object only after the agent has reproduced the failure,
  and never in an acceptance (`Q`) test: a red one means the app is wrong.
- The session's video and dashboard links from `listSessions` go into the bug report; the files are not
  committed.

### `appium-mcp` against a cloud hub

To drive a farm device live (a screen only a real device shows), create the `appium-mcp` session with
`remoteServerUrl` set to the farm's hub, and add two variables to the server's registration:

- `REMOTE_SERVER_URL_ALLOW_REGEX` pins the hubs it may reach, for example
  `'^https://([^@/]+@)?hub-cloud\.browserstack\.com/wd/hub/?$'`. Unset, any HTTP(S) URL is accepted.
- `REMOTE_SERVER_ENABLE_DIRECT_CONNECT=false` stops the client following the hub's direct-connect answer to a
  host the regex never checked.

Never build `remoteServerUrl` from pull-request content, repository data or a prompt: it comes from the
trusted MCP or CI configuration. `appium-mcp` redacts credentials in a hub URL from its logs and errors, but
a persisted session file keeps them: leave `APPIUM_MCP_PERSIST_REMOTE_SESSIONS_PATH` unset, or point it at a
directory only the MCP process owns.
