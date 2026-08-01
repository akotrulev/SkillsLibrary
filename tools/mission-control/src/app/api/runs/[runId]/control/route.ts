import { NextResponse } from "next/server";
import {
  cancelRun,
  isRunning,
  pauseRun,
  retryTask,
  skipTask,
  startRun,
} from "@/lib/orchestrator";
import { loadRun } from "@/lib/store";

export const dynamic = "force-dynamic";
export const maxDuration = 3600;

type Action = "start" | "pause" | "cancel" | "retryTask" | "skipTask";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const run = await loadRun(runId);
  if (!run) return NextResponse.json({ error: "Run not found." }, { status: 404 });

  let body: { action?: Action; taskId?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  switch (body.action) {
    case "start": {
      if (isRunning(runId)) {
        return NextResponse.json({ ok: true, alreadyRunning: true });
      }
      // Drive the run in the background; the board follows over SSE.
      void startRun(runId).catch(() => undefined);
      return NextResponse.json({ ok: true });
    }
    case "pause":
      await pauseRun(runId);
      return NextResponse.json({ ok: true });
    case "cancel":
      await cancelRun(runId);
      return NextResponse.json({ ok: true });
    case "retryTask": {
      if (!body.taskId) {
        return NextResponse.json({ error: "taskId is required." }, { status: 400 });
      }
      await retryTask(runId, body.taskId);
      return NextResponse.json({ ok: true });
    }
    case "skipTask": {
      if (!body.taskId) {
        return NextResponse.json({ error: "taskId is required." }, { status: 400 });
      }
      await skipTask(runId, body.taskId);
      return NextResponse.json({ ok: true });
    }
    default:
      return NextResponse.json({ error: "Unknown action." }, { status: 400 });
  }
}
