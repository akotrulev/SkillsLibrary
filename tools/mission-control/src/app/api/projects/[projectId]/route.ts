import { NextResponse } from "next/server";
import { deleteProject, getProject, setProjectEnabled } from "@/lib/projects";
import { pauseRun } from "@/lib/orchestrator";
import { listRuns } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;

  let body: { enabled?: boolean };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (typeof body.enabled !== "boolean") {
    return NextResponse.json({ error: "`enabled` must be a boolean." }, { status: 400 });
  }

  const project = await setProjectEnabled(projectId, body.enabled);
  if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });

  // Turning execution off stops in-flight work immediately rather than waiting
  // for the current task to finish.
  if (!body.enabled) {
    const runs = await listRuns();
    await Promise.all(
      runs
        .filter((r) => r.targetDir === project.targetDir && r.status === "running")
        .map((r) => pauseRun(r.id)),
    );
  }

  return NextResponse.json(project);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });
  await deleteProject(projectId);
  return NextResponse.json({ ok: true });
}
