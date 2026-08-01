"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  LinearProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { ProjectsPanel, type ProjectRow } from "@/components/ProjectsPanel";

interface RunSummary {
  id: string;
  title: string;
  status: string;
  targetDir: string;
  taskCount: number;
  doneCount: number;
  openQuestionCount: number;
  createdAt: string;
}

interface CatalogInfo {
  agentCount: number;
  skillCount: number;
  libraryRoot: string;
}

export default function HomePage() {
  const router = useRouter();
  const [planText, setPlanText] = useState("");
  const [targetDir, setTargetDir] = useState("");
  const [title, setTitle] = useState("");
  const [planning, setPlanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [catalog, setCatalog] = useState<CatalogInfo | null>(null);
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [selectedDir, setSelectedDir] = useState<string | null>(null);

  const refresh = useCallback(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then(setRuns)
      .catch(() => undefined);
    fetch("/api/projects")
      .then((r) => r.json())
      .then(setProjects)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    refresh();
    fetch("/api/catalog")
      .then((r) => r.json())
      .then((c) => setCatalog(c))
      .catch(() => undefined);
  }, [refresh]);

  // Filter the board by the selected project, when one is chosen.
  const visibleRuns = useMemo(
    () => (selectedDir ? runs.filter((r) => r.targetDir === selectedDir) : runs),
    [runs, selectedDir],
  );

  async function submit() {
    setError(null);
    setPlanning(true);
    try {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          planText,
          targetDir: targetDir || selectedDir || "",
          title,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Planning failed.");
      router.push(`/runs/${data.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Planning failed.");
      setPlanning(false);
    }
  }

  return (
    <Container maxWidth="lg" sx={{ py: 5 }}>
      <Stack direction="row" spacing={2} sx={{ mb: 1, alignItems: "baseline" }}>
        <Typography variant="h1">Mission Control</Typography>
        {catalog && (
          <Typography variant="caption" color="text.secondary">
            {catalog.agentCount} agents · {catalog.skillCount} skills
          </Typography>
        )}
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Give it a plan and a directory. It splits the plan into phased tasks, assigns an
        agent from the SkillsLibrary to each, and runs them — sequentially where order
        matters, in parallel where it is safe.
      </Typography>

      <ProjectsPanel
        projects={projects}
        selectedDir={selectedDir}
        onSelect={setSelectedDir}
        onChanged={refresh}
      />

      <Paper variant="outlined" sx={{ p: 3, mb: 5 }}>
        <Stack spacing={2.5}>
          <TextField
            label="Target directory"
            placeholder="/Users/you/code/my-project"
            value={targetDir || selectedDir || ""}
            onChange={(e) => setTargetDir(e.target.value)}
            fullWidth
            size="small"
            helperText="Absolute path to the repository the agents will work in."
            disabled={planning}
          />
          <TextField
            label="Run title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            fullWidth
            size="small"
            disabled={planning}
          />
          <TextField
            label="Plan"
            placeholder="Paste your plan — phases, features, constraints…"
            value={planText}
            onChange={(e) => setPlanText(e.target.value)}
            fullWidth
            multiline
            minRows={10}
            disabled={planning}
          />
          {error && <Alert severity="error">{error}</Alert>}
          {planning && (
            <Box>
              <LinearProgress />
              <Typography variant="caption" color="text.secondary">
                Planning — reading the target repo and building the task graph. This can
                take a few minutes.
              </Typography>
            </Box>
          )}
          <Box>
            <Button
              variant="contained"
              onClick={submit}
              disabled={
                planning || !planText.trim() || !(targetDir.trim() || selectedDir)
              }
              startIcon={planning ? <CircularProgress size={16} /> : undefined}
            >
              {planning ? "Planning…" : "Plan this run"}
            </Button>
          </Box>
        </Stack>
      </Paper>

      <Typography variant="h2" sx={{ mb: 2 }}>
        Runs
      </Typography>
      {visibleRuns.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No runs yet.
        </Typography>
      ) : (
        <Stack spacing={1}>
          {visibleRuns.map((run) => (
            <Paper
              key={run.id}
              variant="outlined"
              component={Link}
              href={`/runs/${run.id}`}
              sx={{
                p: 2,
                display: "block",
                textDecoration: "none",
                color: "inherit",
                "&:hover": { borderColor: "primary.main" },
              }}
            >
              <Stack
                direction="row"
                spacing={2}
                sx={{ justifyContent: "space-between", alignItems: "center" }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="body1" noWrap>
                    {run.title}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" noWrap>
                    {run.targetDir}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexShrink: 0 }}>
                  {run.openQuestionCount > 0 && (
                    <Chip
                      size="small"
                      color="warning"
                      variant="outlined"
                      label={`${run.openQuestionCount} open`}
                    />
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {run.doneCount}/{run.taskCount}
                  </Typography>
                  <Chip size="small" label={run.status} />
                </Stack>
              </Stack>
            </Paper>
          ))}
        </Stack>
      )}

      {catalog && (
        <>
          <Divider sx={{ my: 4 }} />
          <Typography variant="caption" color="text.secondary">
            Library: {catalog.libraryRoot}
          </Typography>
        </>
      )}
    </Container>
  );
}
