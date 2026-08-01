"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  LinearProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import type { Task, TaskStatus } from "@/lib/types";

const STATUS_COLOR: Record<
  TaskStatus,
  "default" | "primary" | "success" | "warning" | "error" | "info"
> = {
  backlog: "default",
  ready: "info",
  in_progress: "primary",
  review: "secondary" as "primary",
  done: "success",
  blocked: "error",
  skipped: "default",
};

interface Props {
  task: Task;
  runId: string;
  onChanged: () => void;
}

export function TaskCard({ task, runId, onChanged }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);

  const recentLog = task.log.slice(-6);

  async function control(action: "retryTask" | "skipTask") {
    setBusy(true);
    try {
      await fetch(`/api/runs/${runId}/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, taskId: task.id }),
      });
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.5,
        mb: 1,
        borderColor: task.status === "in_progress" ? "primary.main" : undefined,
      }}
    >
      <Stack
        direction="row"
        spacing={1}
        sx={{ justifyContent: "space-between", alignItems: "flex-start" }}
      >
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {task.title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {task.id} · {task.agent}
          </Typography>
        </Box>
        <Chip size="small" color={STATUS_COLOR[task.status]} label={task.status} />
      </Stack>

      {task.status === "in_progress" && <LinearProgress sx={{ mt: 1 }} />}

      {task.skills.length > 0 && (
        <Stack direction="row" sx={{ mt: 1, flexWrap: "wrap", gap: 0.5 }}>
          {task.skills.slice(0, 4).map((skill) => (
            <Chip
              key={skill}
              size="small"
              variant="outlined"
              label={skill}
              sx={{ height: 20, fontSize: "0.65rem" }}
            />
          ))}
          {task.skills.length > 4 && (
            <Chip
              size="small"
              variant="outlined"
              label={`+${task.skills.length - 4}`}
              sx={{ height: 20, fontSize: "0.65rem" }}
            />
          )}
        </Stack>
      )}

      {task.summary && (
        <Alert severity="success" sx={{ mt: 1, py: 0.25 }}>
          <Typography variant="caption">{task.summary}</Typography>
        </Alert>
      )}

      {task.error && (
        <Alert severity="error" sx={{ mt: 1, py: 0.25 }}>
          <Typography variant="caption">{task.error}</Typography>
        </Alert>
      )}

      {task.status === "in_progress" && recentLog.length > 0 && (
        <Box
          sx={{
            mt: 1,
            p: 1,
            bgcolor: "rgba(0,0,0,0.35)",
            borderRadius: 1,
            maxHeight: 120,
            overflow: "auto",
          }}
        >
          {recentLog.map((entry, i) => (
            <Typography
              key={i}
              variant="caption"
              sx={{ display: "block", fontFamily: "ui-monospace, monospace",
                fontSize: "0.68rem",
                color: entry.kind === "tool" ? "info.main" : "text.secondary",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {entry.text.length > 200 ? `${entry.text.slice(0, 200)}…` : entry.text}
            </Typography>
          ))}
        </Box>
      )}

      <Stack direction="row" spacing={1} sx={{ mt: 1, alignItems: "center" }}>
        <Button size="small" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Less" : "Details"}
        </Button>
        {task.status === "blocked" && (
          <Button size="small" onClick={() => control("retryTask")} disabled={busy}>
            Retry
          </Button>
        )}
        {(task.status === "blocked" || task.status === "ready") && (
          <Button size="small" color="inherit" onClick={() => control("skipTask")} disabled={busy}>
            Skip
          </Button>
        )}
        {task.costUsd !== undefined && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
            ${task.costUsd.toFixed(3)}
          </Typography>
        )}
      </Stack>

      <Collapse in={expanded}>
        <Box sx={{ mt: 1.5 }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
            Intent
          </Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            {task.intent}
          </Typography>

          {task.acceptanceCriteria.length > 0 && (
            <>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                Acceptance criteria
              </Typography>
              <Box component="ul" sx={{ m: 0, mb: 1, pl: 2.5 }}>
                {task.acceptanceCriteria.map((c, i) => (
                  <Typography key={i} component="li" variant="body2">
                    {c}
                  </Typography>
                ))}
              </Box>
            </>
          )}

          {task.files.length > 0 && (
            <>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                Files
              </Typography>
              <Typography
                variant="caption"
                sx={{ fontFamily: "ui-monospace, monospace", wordBreak: "break-all" }}
              >
                {task.files.join(", ")}
              </Typography>
            </>
          )}

          {task.dependsOn.length > 0 && (
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              Depends on: {task.dependsOn.join(", ")}
            </Typography>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
}
