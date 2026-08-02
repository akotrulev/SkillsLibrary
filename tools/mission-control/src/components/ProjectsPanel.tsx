"use client";

import { useState } from "react";
import VpnKeyIcon from "@mui/icons-material/VpnKey";
import {
  Box,
  Button,
  Chip,
  Collapse,
  IconButton,
  Paper,
  Stack,
  Switch,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import { GitHubAccess } from "./GitHubAccess";

export interface ProjectRow {
  id: string;
  name: string;
  targetDir: string;
  enabled: boolean;
  source: "local" | "git";
  repoUrl?: string;
  workBranch?: string;
  runCount: number;
  activeRunCount: number;
}

interface Props {
  projects: ProjectRow[];
  selectedDir: string | null;
  onSelect: (targetDir: string | null) => void;
  onChanged: () => void;
}

/**
 * Project registry with the per-project execution switch.
 *
 * Turning a project off pauses its running work and blocks further dispatch;
 * all plans, tasks and summaries stay exactly where they are.
 */
export function ProjectsPanel({ projects, selectedDir, onSelect, onChanged }: Props) {
  const [adding, setAdding] = useState(false);
  const [mode, setMode] = useState<"local" | "git">("local");
  const [dir, setDir] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  /** Which project has its GitHub access section open. */
  const [keyOpenId, setKeyOpenId] = useState<string | null>(null);

  /** Commit + push a git project's work branch. */
  async function pushWork(project: ProjectRow) {
    setBusyId(project.id);
    setError(null);
    setNotice(null);
    try {
      const commit = await fetch(`/api/projects/${project.id}/git`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "commit" }),
      }).then((r) => r.json());
      if (commit.error) throw new Error(commit.error);

      const push = await fetch(`/api/projects/${project.id}/git`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "push" }),
      }).then((r) => r.json());
      if (push.error) throw new Error(push.error);

      setNotice(
        commit.committed
          ? `Committed and pushed ${project.workBranch}.`
          : `Nothing new to commit; pushed ${project.workBranch}.`,
      );
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Push failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function toggle(project: ProjectRow) {
    setBusyId(project.id);
    try {
      await fetch(`/api/projects/${project.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !project.enabled }),
      });
      onChanged();
    } finally {
      setBusyId(null);
    }
  }

  async function add() {
    setError(null);
    const payload =
      mode === "git" ? { repoUrl, name } : { targetDir: dir, name };
    const response = await fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setError(data.error ?? "Could not add project.");
      return;
    }
    setDir("");
    setRepoUrl("");
    setName("");
    setAdding(false);
    onChanged();
  }

  return (
    <Paper variant="outlined" sx={{ p: 2.5, mb: 4 }}>
      <Stack
        direction="row"
        spacing={1.5}
        sx={{ mb: 1.5, alignItems: "center", justifyContent: "space-between" }}
      >
        <Typography variant="h2">Projects</Typography>
        <Button size="small" onClick={() => setAdding((v) => !v)}>
          {adding ? "Cancel" : "Add project"}
        </Button>
      </Stack>

      {adding && (
        <Box sx={{ mb: 2 }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={mode}
            onChange={(_e, v) => v && setMode(v)}
            sx={{ mb: 1.5 }}
          >
            <ToggleButton value="local">Local directory</ToggleButton>
            <ToggleButton value="git">GitHub repo</ToggleButton>
          </ToggleButtonGroup>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            {mode === "local" ? (
              <TextField
                size="small"
                label="Directory"
                placeholder="/Users/you/code/project"
                value={dir}
                onChange={(e) => setDir(e.target.value)}
                fullWidth
              />
            ) : (
              <TextField
                size="small"
                label="Repository URL"
                placeholder="https://github.com/owner/repo.git"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                fullWidth
                helperText="Cloned into a managed workspace; work lands on its own branch."
              />
            )}
            <TextField
              size="small"
              label="Name (optional)"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Button
              variant="contained"
              onClick={add}
              disabled={mode === "local" ? !dir.trim() : !repoUrl.trim()}
              sx={{ alignSelf: "flex-start" }}
            >
              Add
            </Button>
          </Stack>
        </Box>
      )}

      {error && (
        <Typography variant="caption" color="error" sx={{ display: "block", mb: 1 }}>
          {error}
        </Typography>
      )}

      {notice && (
        <Typography variant="caption" color="success.main" sx={{ display: "block", mb: 1 }}>
          {notice}
        </Typography>
      )}

      {projects.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No projects yet — planning a run registers its directory automatically.
        </Typography>
      ) : (
        <Stack spacing={0.5}>
          {projects.map((project) => {
            const selected = selectedDir === project.targetDir;
            return (
              <Box
                key={project.id}
                sx={{
                  borderRadius: 1,
                  bgcolor: selected ? "rgba(76,141,255,0.12)" : "transparent",
                  "&:hover": { bgcolor: "rgba(255,255,255,0.04)" },
                }}
              >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, p: 1 }}>
                <Tooltip
                  title={
                    project.enabled
                      ? "Execution on — runs may dispatch agents"
                      : "Execution off — state is kept, nothing dispatches"
                  }
                >
                  <Switch
                    size="small"
                    checked={project.enabled}
                    disabled={busyId === project.id}
                    onChange={() => toggle(project)}
                  />
                </Tooltip>

                <Box
                  sx={{ minWidth: 0, flex: 1, cursor: "pointer" }}
                  onClick={() => onSelect(selected ? null : project.targetDir)}
                >
                  <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                    {project.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" noWrap>
                    {project.source === "git"
                      ? `${project.repoUrl} · ${project.workBranch}`
                      : project.targetDir}
                  </Typography>
                </Box>

                {project.source === "git" && (
                  <Tooltip title="GitHub access for this project">
                    <IconButton
                      size="small"
                      color={keyOpenId === project.id ? "primary" : "default"}
                      onClick={() =>
                        setKeyOpenId(keyOpenId === project.id ? null : project.id)
                      }
                    >
                      <VpnKeyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
                {project.source === "git" && (
                  <Tooltip title="Commit everything in the workspace and push the work branch">
                    <span>
                      <Button
                        size="small"
                        onClick={() => pushWork(project)}
                        disabled={busyId === project.id}
                      >
                        Push
                      </Button>
                    </span>
                  </Tooltip>
                )}
                {project.source === "git" && (
                  <Chip size="small" variant="outlined" label="git" />
                )}
                {project.activeRunCount > 0 && (
                  <Chip size="small" color="primary" label={`${project.activeRunCount} active`} />
                )}
                <Typography variant="caption" color="text.secondary">
                  {project.runCount} run{project.runCount === 1 ? "" : "s"}
                </Typography>
                {!project.enabled && <Chip size="small" label="paused" />}
              </Box>

              {project.source === "git" && (
                <Collapse in={keyOpenId === project.id} unmountOnExit>
                  <GitHubAccess projectId={project.id} repoUrl={project.repoUrl} />
                </Collapse>
              )}
              </Box>
            );
          })}
        </Stack>
      )}
    </Paper>
  );
}
