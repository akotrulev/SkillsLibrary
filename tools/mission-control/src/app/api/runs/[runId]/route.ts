import { NextResponse } from "next/server";
import { cancelRun } from "@/lib/orchestrator";
import { deleteRun, loadRun } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const run = await loadRun(runId);
  if (!run) return NextResponse.json({ error: "Run not found." }, { status: 404 });
  return NextResponse.json(run);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  await cancelRun(runId);
  await deleteRun(runId);
  return NextResponse.json({ ok: true });
}
