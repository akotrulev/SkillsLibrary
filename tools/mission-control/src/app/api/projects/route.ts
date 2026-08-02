import fs from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { createGitProject, listProjects, upsertProject } from "@/lib/projects";
import { listRuns } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function GET() {
  const [projects, runs] = await Promise.all([listProjects(), listRuns()]);
  return NextResponse.json(
    projects.map((project) => {
      const projectRuns = runs.filter((r) => r.targetDir === project.targetDir);
      return {
        ...project,
        runCount: projectRuns.length,
        activeRunCount: projectRuns.filter(
          (r) => r.status === "running" || r.status === "paused",
        ).length,
      };
    }),
  );
}

export async function POST(request: Request) {
  let body: {
    name?: string;
    targetDir?: string;
    repoUrl?: string;
    baseBranch?: string;
    workBranch?: string;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  // Git-backed project: nothing is cloned until the first run prepares it.
  const repoUrl = body.repoUrl?.trim();
  if (repoUrl) {
    if (!/^(https:\/\/|git@)/.test(repoUrl)) {
      return NextResponse.json(
        { error: "Repository URL must start with https:// or git@." },
        { status: 400 },
      );
    }
    const project = await createGitProject({
      repoUrl,
      name: body.name,
      baseBranch: body.baseBranch,
      workBranch: body.workBranch,
    });
    return NextResponse.json(project, { status: 201 });
  }

  const raw = body.targetDir?.trim();
  if (!raw) {
    return NextResponse.json(
      { error: "Provide either a target directory or a repository URL." },
      { status: 400 },
    );
  }

  const targetDir = path.resolve(raw);
  try {
    const stat = await fs.stat(targetDir);
    if (!stat.isDirectory()) {
      return NextResponse.json({ error: `${targetDir} is not a directory.` }, { status: 400 });
    }
  } catch {
    return NextResponse.json(
      { error: `Directory does not exist: ${targetDir}` },
      { status: 400 },
    );
  }

  const project = await upsertProject({ name: body.name, targetDir });
  return NextResponse.json(project, { status: 201 });
}
