"use client";

import { useState } from "react";
import {
  Box,
  Button,
  Chip,
  IconButton,
  Paper,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

export interface ProjectRow {
  id: string;
  name: string;
  targetDir: string;
  enabled: boolean;
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
  const [dir, setDir] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

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
    const response = await fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ targetDir: dir, name }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setError(data.error ?? "Could not add project.");
      return;
    }
    setDir("");
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
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
          <TextField
            size="small"
            label="Directory"
            placeholder="/Users/you/code/project"
            value={dir}
            onChange={(e) => setDir(e.target.value)}
            fullWidth
          />
          <TextField
            size="small"
            label="Name (optional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Button variant="contained" onClick={add} disabled={!dir.trim()}>
            Add
          </Button>
        </Stack>
      )}

      {error && (
        <Typography variant="caption" color="error" sx={{ display: "block", mb: 1 }}>
          {error}
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
                  display: "flex",
                  alignItems: "center",
                  gap: 1.5,
                  p: 1,
                  borderRadius: 1,
                  bgcolor: selected ? "rgba(76,141,255,0.12)" : "transparent",
                  "&:hover": { bgcolor: "rgba(255,255,255,0.04)" },
                }}
              >
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
                    {project.targetDir}
                  </Typography>
                </Box>

                {project.activeRunCount > 0 && (
                  <Chip size="small" color="primary" label={`${project.activeRunCount} active`} />
                )}
                <Typography variant="caption" color="text.secondary">
                  {project.runCount} run{project.runCount === 1 ? "" : "s"}
                </Typography>
                {!project.enabled && <Chip size="small" label="paused" />}
              </Box>
            );
          })}
        </Stack>
      )}
    </Paper>
  );
}
