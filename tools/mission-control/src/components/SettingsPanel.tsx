"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

/** Mirrors `HostConfig`'s per-credential detection. */
interface Detection {
  status: "found" | "likely" | "absent";
  label: string;
  via?: "env" | "file" | "cli" | "helper";
}

interface CredentialState {
  source: "configured" | "host" | "none";
  hint?: string;
  envName?: string;
  undecryptable: boolean;
  host: Detection;
}

export interface SettingsView {
  anthropic: CredentialState;
  github: CredentialState;
  gitIdentity: Detection;
  plannerModel: string;
  implementerModel: string;
  maxParallel: number;
  anthropicBaseUrl?: string;
  strongKeyStorage: boolean;
  storageAvailable: boolean;
  host: { platform: string; homeDir: string; detectedAt: string };
}

const ANTHROPIC_ENV_NAMES = [
  "ANTHROPIC_API_KEY",
  "CLAUDE_CODE_OAUTH_TOKEN",
  "ANTHROPIC_AUTH_TOKEN",
] as const;

/**
 * Where a credential is coming from, in one chip.
 *
 * The three states are worth distinguishing precisely because the whole point
 * of this panel is that you should not have to configure what the machine
 * already provides: "Using this machine" means leave it alone.
 */
function SourceChip({ state }: { state: CredentialState }) {
  if (state.undecryptable) {
    return <Chip size="small" color="error" label="Stored but unreadable — re-enter" />;
  }
  if (state.source === "configured") {
    return <Chip size="small" color="primary" label={`Configured here ${state.hint ?? ""}`} />;
  }
  if (state.source === "host") {
    return (
      <Chip
        size="small"
        color={state.host.status === "found" ? "success" : "warning"}
        variant="outlined"
        label={state.host.status === "found" ? "Using this machine" : "Probably on this machine"}
      />
    );
  }
  return <Chip size="small" color="error" variant="outlined" label="Not configured" />;
}

/**
 * Instance settings — credentials, models, concurrency.
 *
 * Two properties the UI has to make obvious, because they are the reason this
 * exists: **what the host already provides is used unless you override it**,
 * and **a value you type is never shown back to you**. Every field therefore
 * starts empty regardless of what is stored, and the stored value is
 * represented by its last four characters and nothing more.
 */
export function SettingsPanel() {
  const [view, setView] = useState<SettingsView | null>(null);
  const [anthropicValue, setAnthropicValue] = useState("");
  const [anthropicEnvName, setAnthropicEnvName] =
    useState<(typeof ANTHROPIC_ENV_NAMES)[number]>("ANTHROPIC_API_KEY");
  const [githubValue, setGithubValue] = useState("");
  const [plannerModel, setPlannerModel] = useState("");
  const [implementerModel, setImplementerModel] = useState("");
  const [maxParallel, setMaxParallel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/settings");
      if (!response.ok) return;
      const data: SettingsView = await response.json();
      setView(data);
      setPlannerModel(data.plannerModel);
      setImplementerModel(data.implementerModel);
      setMaxParallel(String(data.maxParallel));
      setBaseUrl(data.anthropicBaseUrl ?? "");
      if (data.anthropic.envName) {
        setAnthropicEnvName(data.anthropic.envName as (typeof ANTHROPIC_ENV_NAMES)[number]);
      }
    } catch {
      // Informational panel: keep whatever was last rendered.
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function save(body: Record<string, unknown>, message: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error ?? "Could not save.");
      setView(payload as SettingsView);
      setNotice(message);
      // Never leave a secret sitting in a DOM node after it is stored.
      setAnthropicValue("");
      setGithubValue("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  if (!view) return null;

  const parallel = Number(maxParallel);
  const parallelInvalid = maxParallel.trim() !== "" && (!Number.isFinite(parallel) || parallel < 1);

  return (
    <Accordion variant="outlined" disableGutters sx={{ mb: 3 }}>
      <AccordionSummary>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", flexWrap: "wrap" }}>
          <Typography variant="body1">Settings</Typography>
          <Chip
            size="small"
            variant="outlined"
            color={view.anthropic.source === "none" ? "error" : "default"}
            label={`Claude: ${view.anthropic.source === "none" ? "not configured" : "ready"}`}
          />
          <Chip
            size="small"
            variant="outlined"
            color={view.github.source === "none" ? "warning" : "default"}
            label={`GitHub: ${view.github.source === "none" ? "not configured" : "ready"}`}
          />
        </Stack>
      </AccordionSummary>

      <AccordionDetails>
        <Stack spacing={3}>
          <Typography variant="body2" color="text.secondary">
            Anything this machine already provides is used as-is — a value here overrides it.
            Credentials are stored encrypted and never shown again after saving.
          </Typography>

          {!view.storageAvailable && (
            <Alert severity="error">
              The data directory is not writable, so no credential can be stored. Fix its
              permissions, or configure credentials through the environment instead.
            </Alert>
          )}

          {/* --- Claude ------------------------------------------------- */}
          <Box>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", mb: 1 }}>
              <Typography variant="subtitle2">Claude</Typography>
              <SourceChip state={view.anthropic} />
            </Stack>
            <Typography variant="caption" color="text.secondary">
              Detected on this machine: {view.anthropic.host.label}
            </Typography>

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mt: 1.5 }}>
              <TextField
                label="API key or token"
                type="password"
                placeholder={view.anthropic.source === "configured" ? "•••• stored" : "sk-ant-…"}
                value={anthropicValue}
                onChange={(e) => setAnthropicValue(e.target.value)}
                size="small"
                fullWidth
                autoComplete="off"
                disabled={busy || !view.storageAvailable}
              />
              <TextField
                label="Set as"
                select
                value={anthropicEnvName}
                onChange={(e) =>
                  setAnthropicEnvName(e.target.value as (typeof ANTHROPIC_ENV_NAMES)[number])
                }
                size="small"
                sx={{ minWidth: 240 }}
                disabled={busy}
                helperText="Which variable the agent process receives"
              >
                {ANTHROPIC_ENV_NAMES.map((name) => (
                  <MenuItem key={name} value={name}>
                    {name}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>

            <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
              <Button
                size="small"
                variant="contained"
                disabled={busy || !anthropicValue.trim()}
                onClick={() =>
                  save(
                    {
                      anthropicCredential: anthropicValue,
                      anthropicEnvName,
                    },
                    "Claude credential saved. It applies to the next task dispatched.",
                  )
                }
              >
                Save
              </Button>
              {view.anthropic.source === "configured" && (
                <Button
                  size="small"
                  color="inherit"
                  disabled={busy}
                  onClick={() =>
                    save(
                      { anthropicCredential: null },
                      "Cleared — falling back to whatever this machine provides.",
                    )
                  }
                >
                  Clear
                </Button>
              )}
            </Stack>
          </Box>

          <Divider />

          {/* --- GitHub ------------------------------------------------- */}
          <Box>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", mb: 1 }}>
              <Typography variant="subtitle2">GitHub</Typography>
              <SourceChip state={view.github} />
            </Stack>
            <Stack spacing={0.25}>
              <Typography variant="caption" color="text.secondary">
                Detected on this machine: {view.github.host.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Commit author: {view.gitIdentity.label}
              </Typography>
            </Stack>

            <Stack direction="row" spacing={1.5} sx={{ mt: 1.5 }}>
              <TextField
                label="Personal access token"
                type="password"
                placeholder={view.github.source === "configured" ? "•••• stored" : "ghp_…"}
                value={githubValue}
                onChange={(e) => setGithubValue(e.target.value)}
                size="small"
                fullWidth
                autoComplete="off"
                disabled={busy || !view.storageAvailable}
                helperText="Only needed when git cannot authenticate on its own. Projects may override this individually."
              />
            </Stack>

            <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
              <Button
                size="small"
                variant="contained"
                disabled={busy || !githubValue.trim()}
                onClick={() => save({ githubToken: githubValue }, "GitHub token saved.")}
              >
                Save
              </Button>
              {view.github.source === "configured" && (
                <Button
                  size="small"
                  color="inherit"
                  disabled={busy}
                  onClick={() =>
                    save(
                      { githubToken: null },
                      "Cleared — falling back to whatever this machine provides.",
                    )
                  }
                >
                  Clear
                </Button>
              )}
            </Stack>
          </Box>

          <Divider />

          {/* --- Models and concurrency --------------------------------- */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
              Models and concurrency
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <TextField
                label="Planner model"
                value={plannerModel}
                onChange={(e) => setPlannerModel(e.target.value)}
                size="small"
                fullWidth
                disabled={busy}
              />
              <TextField
                label="Implementer model"
                value={implementerModel}
                onChange={(e) => setImplementerModel(e.target.value)}
                size="small"
                fullWidth
                disabled={busy}
              />
              <TextField
                label="Max parallel"
                value={maxParallel}
                onChange={(e) => setMaxParallel(e.target.value)}
                size="small"
                sx={{ minWidth: 140 }}
                disabled={busy}
                error={parallelInvalid}
                helperText={parallelInvalid ? "1 or more" : "Within a parallel-safe phase"}
              />
            </Stack>
            <TextField
              label="Anthropic base URL (optional)"
              placeholder="https://gateway.example.com"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              size="small"
              fullWidth
              sx={{ mt: 1.5 }}
              disabled={busy}
              helperText="For an Anthropic-compatible gateway or proxy. Leave empty for the API."
            />
            <Button
              size="small"
              variant="contained"
              sx={{ mt: 1.5 }}
              disabled={busy || parallelInvalid}
              onClick={() =>
                save(
                  {
                    plannerModel: plannerModel.trim() || null,
                    implementerModel: implementerModel.trim() || null,
                    maxParallel: maxParallel.trim() ? Number(maxParallel) : null,
                    anthropicBaseUrl: baseUrl.trim() || null,
                  },
                  "Saved. New runs use these; runs already planned keep their own values.",
                )
              }
            >
              Save
            </Button>
          </Box>

          {error && <Alert severity="error">{error}</Alert>}
          {notice && <Alert severity="success">{notice}</Alert>}

          <Typography variant="caption" color="text.secondary">
            {view.host.platform} · home {view.host.homeDir} ·{" "}
            {view.strongKeyStorage
              ? "encryption key from MISSION_CONTROL_SECRET"
              : "encryption key stored beside the data"}
          </Typography>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}
