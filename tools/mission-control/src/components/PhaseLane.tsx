"use client";

import { Box, Chip, Paper, Stack, Tooltip, Typography } from "@mui/material";
import { TaskCard } from "./TaskCard";
import type { Phase, Task, TaskStatus } from "@/lib/types";

/** Board columns, in flow order. */
const COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: "backlog", label: "Backlog" },
  { status: "ready", label: "Ready" },
  { status: "in_progress", label: "In progress" },
  { status: "done", label: "Done" },
  { status: "blocked", label: "Blocked" },
];

interface Props {
  phase: Phase;
  tasks: Task[];
  runId: string;
  onChanged: () => void;
}

/**
 * One phase, rendered as its own Kanban strip. Phases are the unit of ordering,
 * so keeping each in its own lane makes the sequential/parallel boundary and
 * the current front of execution obvious at a glance.
 */
export function PhaseLane({ phase, tasks, runId, onChanged }: Props) {
  const skipped = tasks.filter((t) => t.status === "skipped");
  const done = tasks.filter((t) => t.status === "done").length;

  return (
    <Box sx={{ mb: 4 }}>
      <Stack direction="row" spacing={1.5} sx={{ mb: 1, alignItems: "center" }}>
        <Typography variant="h2">
          {phase.index + 1}. {phase.name}
        </Typography>
        <Tooltip title={phase.parallelRationale || "No rationale given"}>
          <Chip
            size="small"
            color={phase.parallelSafe ? "success" : "default"}
            variant={phase.parallelSafe ? "filled" : "outlined"}
            label={phase.parallelSafe ? "parallel" : "sequential"}
          />
        </Tooltip>
        <Typography variant="caption" color="text.secondary">
          {done}/{tasks.length} done
        </Typography>
      </Stack>

      {phase.goal && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          {phase.goal}
        </Typography>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md: "repeat(2, minmax(0,1fr))",
            lg: "repeat(5, minmax(0,1fr))",
          },
          gap: 1.5,
          alignItems: "start",
        }}
      >
        {COLUMNS.map((column) => {
          const columnTasks = tasks.filter((t) => t.status === column.status);
          return (
            <Paper
              key={column.status}
              variant="outlined"
              sx={{ p: 1, bgcolor: "rgba(255,255,255,0.02)", minHeight: 80 }}
            >
              <Stack direction="row" sx={{ mb: 1, justifyContent: "space-between" }}>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                  {column.label}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {columnTasks.length}
                </Typography>
              </Stack>
              {columnTasks.map((task) => (
                <TaskCard key={task.id} task={task} runId={runId} onChanged={onChanged} />
              ))}
            </Paper>
          );
        })}
      </Box>

      {skipped.length > 0 && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
          Skipped: {skipped.map((t) => t.id).join(", ")}
        </Typography>
      )}
    </Box>
  );
}
