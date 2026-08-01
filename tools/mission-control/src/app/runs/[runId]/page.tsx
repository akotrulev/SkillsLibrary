"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Stack,
  Typography,
} from "@mui/material";
import { OpenQuestions } from "@/components/OpenQuestions";
import { PhaseLane } from "@/components/PhaseLane";
import type { Run, RunEvent } from "@/lib/types";

export default function RunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = use(params);
  const [run, setRun] = useState<Run | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  const refresh = useCallback(async () => {
    const response = await fetch(`/api/runs/${runId}`);
    if (response.ok) setRun(await response.json());
  }, [runId]);

  // Live updates. The stream primes itself with current state on connect, so
  // there is no separate initial fetch to race against.
  useEffect(() => {
    const source = new EventSource(`/api/runs/${runId}/events`);
    sourceRef.current = source;

    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as RunEvent;
      if (event.type === "run:updated") {
        setRun(event.run);
      } else if (event.type === "task:updated") {
        setRun((prev) =>
          prev
            ? {
                ...prev,
                tasks: prev.tasks.map((t) => (t.id === event.task.id ? event.task : t)),
              }
            : prev,
        );
      } else if (event.type === "task:log") {
        setRun((prev) =>
          prev
            ? {
                ...prev,
                tasks: prev.tasks.map((t) =>
                  t.id === event.taskId ? { ...t, log: [...t.log, event.entry] } : t,
                ),
              }
            : prev,
        );
      }
    };

    source.onerror = () => setLoadError("Live connection lost. Reload to reconnect.");

    return () => source.close();
  }, [runId]);

  async function control(action: "start" | "pause" | "cancel") {
    setBusy(true);
    try {
      await fetch(`/api/runs/${runId}/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  if (!run) {
    return (
      <Container sx={{ py: 6 }}>
        <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
          <CircularProgress size={20} />
          <Typography variant="body2">Loading run…</Typography>
        </Stack>
        {loadError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {loadError}
          </Alert>
        )}
      </Container>
    );
  }

  const blockingUnanswered = run.openQuestions.filter(
    (q) => !q.answer && q.blocksTaskIds.length > 0,
  ).length;
  const done = run.tasks.filter((t) => t.status === "done").length;
  const totalCost = run.tasks.reduce((sum, t) => sum + (t.costUsd ?? 0), 0);
  const canStart = run.status !== "running" && run.status !== "completed";

  return (
    <Container maxWidth={false} sx={{ py: 4, px: { xs: 2, lg: 4 } }}>
      <Button component={Link} href="/" size="small" sx={{ mb: 2 }}>
        ← All runs
      </Button>

      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        sx={{ mb: 1, justifyContent: "space-between", alignItems: { md: "center" } }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <Typography variant="h1">{run.title}</Typography>
            <Chip
              size="small"
              label={run.status}
              color={
                run.status === "running"
                  ? "primary"
                  : run.status === "completed"
                    ? "success"
                    : run.status === "failed"
                      ? "error"
                      : "default"
              }
            />
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {run.targetDir} · {done}/{run.tasks.length} tasks
            {totalCost > 0 && ` · $${totalCost.toFixed(2)}`}
          </Typography>
        </Box>

        <Stack direction="row" spacing={1}>
          <Button
            variant="contained"
            disabled={busy || !canStart || blockingUnanswered > 0}
            onClick={() => control("start")}
          >
            {run.status === "paused" || done > 0 ? "Resume" : "Start"}
          </Button>
          <Button
            variant="outlined"
            disabled={busy || run.status !== "running"}
            onClick={() => control("pause")}
          >
            Pause
          </Button>
          <Button
            variant="outlined"
            color="error"
            disabled={busy || run.status === "completed"}
            onClick={() => control("cancel")}
          >
            Cancel
          </Button>
        </Stack>
      </Stack>

      {blockingUnanswered > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {blockingUnanswered} unanswered question
          {blockingUnanswered === 1 ? "" : "s"} gate tasks in this run. Answer below to
          start.
        </Alert>
      )}

      {run.error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {run.error}
        </Alert>
      )}

      {run.planningNotes && (
        <Alert severity="info" sx={{ mb: 3 }}>
          {run.planningNotes}
        </Alert>
      )}

      <OpenQuestions runId={run.id} questions={run.openQuestions} onAnswered={refresh} />

      {run.phases.map((phase) => (
        <PhaseLane
          key={phase.id}
          phase={phase}
          tasks={run.tasks.filter((t) => t.phaseId === phase.id)}
          runId={run.id}
          onChanged={refresh}
        />
      ))}
    </Container>
  );
}
