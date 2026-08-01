import fs from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { planRun } from "@/lib/planner";
import { upsertProject } from "@/lib/projects";
import { listRuns, saveRun } from "@/lib/store";

export const dynamic = "force-dynamic";
/** Planning reads the target repo and can take a few minutes. */
export const maxDuration = 3600;

export async function GET() {
  const runs = await listRuns();
  return NextResponse.json(
    runs.map((r) => ({
      id: r.id,
      title: r.title,
      status: r.status,
      targetDir: r.targetDir,
      taskCount: r.tasks.length,
      doneCount: r.tasks.filter((t) => t.status === "done").length,
      openQuestionCount: r.openQuestions.filter((q) => !q.answer).length,
      createdAt: r.createdAt,
      updatedAt: r.updatedAt,
    })),
  );
}

export async function POST(request: Request) {
  let body: { planText?: string; targetDir?: string; title?: string; maxParallel?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const planText = body.planText?.trim();
  const targetDirRaw = body.targetDir?.trim();

  if (!planText) {
    return NextResponse.json({ error: "A plan is required." }, { status: 400 });
  }
  if (!targetDirRaw) {
    return NextResponse.json({ error: "A target directory is required." }, { status: 400 });
  }

  const targetDir = path.resolve(targetDirRaw);
  try {
    const stat = await fs.stat(targetDir);
    if (!stat.isDirectory()) {
      return NextResponse.json(
        { error: `${targetDir} is not a directory.` },
        { status: 400 },
      );
    }
  } catch {
    return NextResponse.json(
      { error: `Target directory does not exist: ${targetDir}` },
      { status: 400 },
    );
  }

  try {
    // Registering the directory as a project gives it an execution switch.
    await upsertProject({ targetDir });

    const run = await planRun({
      planText,
      targetDir,
      title: body.title,
      maxParallel: body.maxParallel,
    });
    await saveRun(run);
    return NextResponse.json(run, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Planning failed." },
      { status: 500 },
    );
  }
}
