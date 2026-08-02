"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Chip, Link, Stack, TextField, Typography } from "@mui/material";

/** Client-safe view of a project's credential. Never carries the token. */
export interface TokenDescriptor {
  source: "project" | "env" | "none";
  hint?: string;
  canPush: boolean;
  undecryptable: boolean;
  storageAvailable: boolean;
}

interface Props {
  projectId: string;
  repoUrl?: string;
}

/**
 * Per-project GitHub credential.
 *
 * The token is write-only: it is sent on save and never read back, so the field
 * always starts empty and the stored value is represented only by its last four
 * characters.
 */
export function GitHubAccess({ projectId, repoUrl }: Props) {
  const [descriptor, setDescriptor] = useState<TokenDescriptor | null>(null);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/token`);
      if (response.ok) setDescriptor(await response.json());
    } catch {
      // Leave the previous descriptor; the section is informational.
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function send(
    method: "PUT" | "DELETE" | "POST",
    body?: Record<string, unknown>,
  ): Promise<unknown | null> {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(`/api/projects/${projectId}/token`, {
        method,
        headers: body ? { "content-type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(payload.error ?? `Request failed (${response.status}).`);
        return null;
      }
      return payload;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Request failed.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    const result = await send("PUT", { token });
    if (result) {
      setToken("");
      setNotice("Token saved.");
      await refresh();
    }
  }

  async function clear() {
    const result = await send("DELETE");
    if (result) {
      setNotice("Token removed; falling back to the environment token.");
      await refresh();
    }
  }

  async function test() {
    // A typed-but-unsaved token is testable, so a bad paste is caught early.
    const result = (await send("POST", token.trim() ? { token } : {})) as
      | { ok: boolean; reason?: string; verified?: "write" | "read" }
      | null;
    if (!result) return;
    if (!result.ok) {
      setError(result.reason ?? "Could not reach the repository.");
      return;
    }
    setNotice(
      result.verified === "write"
        ? "Write access confirmed — this token can push."
        : "Repository is reachable, but write access is unverified until the workspace is cloned. Run Prepare, then test again.",
    );
  }

  const status = (() => {
    if (!descriptor) return { label: "Checking…", color: "default" as const };
    if (descriptor.undecryptable) {
      return { label: "Stored token unreadable — re-enter it", color: "warning" as const };
    }
    if (descriptor.source === "project") {
      return { label: `Project token · ${descriptor.hint ?? "…"}`, color: "success" as const };
    }
    if (descriptor.source === "env") {
      return { label: "Using environment token", color: "info" as const };
    }
    return { label: "No token — push disabled", color: "default" as const };
  })();

  return (
    <Box sx={{ px: 1, pb: 1.5 }}>
      <Stack spacing={1.5}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
          <Typography variant="caption" color="text.secondary">
            GitHub access
          </Typography>
          <Chip size="small" color={status.color} label={status.label} />
        </Stack>

        {descriptor && !descriptor.storageAvailable && (
          <Alert severity="warning" variant="outlined">
            <code>MISSION_CONTROL_SECRET</code> is not set, so per-project tokens cannot be
            stored encrypted. Set it and restart, or use <code>MISSION_CONTROL_GIT_TOKEN</code>{" "}
            for every project.
          </Alert>
        )}

        {descriptor?.undecryptable && (
          <Alert severity="warning" variant="outlined">
            A token is stored for this project but cannot be decrypted — usually a changed
            <code> MISSION_CONTROL_SECRET</code>. Enter the token again to replace it.
          </Alert>
        )}

        <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start", flexWrap: "wrap" }}>
          <TextField
            size="small"
            type="password"
            label="Personal access token"
            placeholder="github_pat_…"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            autoComplete="off"
            disabled={busy || descriptor?.storageAvailable === false}
            sx={{ flex: 1, minWidth: 260 }}
          />
          <Button
            size="small"
            variant="contained"
            onClick={save}
            disabled={busy || !token.trim() || descriptor?.storageAvailable === false}
          >
            Save
          </Button>
          <Button size="small" onClick={test} disabled={busy || !repoUrl}>
            Test access
          </Button>
          {descriptor?.source === "project" && (
            <Button size="small" color="warning" onClick={clear} disabled={busy}>
              Clear
            </Button>
          )}
        </Stack>

        <Typography variant="caption" color="text.secondary">
          Use a{" "}
          <Link
            href="https://github.com/settings/personal-access-tokens"
            target="_blank"
            rel="noreferrer"
          >
            fine-grained token
          </Link>{" "}
          scoped to this repository with <strong>Contents: read and write</strong>. It is
          encrypted at rest, used only for git commands, and never exposed to agents.
        </Typography>

        {error && (
          <Alert severity="error" variant="outlined" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {notice && (
          <Alert severity="success" variant="outlined" onClose={() => setNotice(null)}>
            {notice}
          </Alert>
        )}
      </Stack>
    </Box>
  );
}
