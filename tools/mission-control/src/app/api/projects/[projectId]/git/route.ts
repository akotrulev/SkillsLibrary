import { NextResponse } from "next/server";
import { commitAll, pushBranch, redact, workspaceStatus } from "@/lib/git";
import { getProject, prepareProject, resolveGitToken, tokenDescriptor } from "@/lib/projects";

export const dynamic = "force-dynamic";
export const maxDuration = 900;

/** Working-tree status for a git-backed project. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });
  if (project.source !== "git") {
    return NextResponse.json({ error: "Not a git-backed project." }, { status: 400 });
  }

  try {
    const status = await workspaceStatus(project.targetDir, project.baseBranch);
    return NextResponse.json({
      repoUrl: project.repoUrl,
      baseBranch: project.baseBranch,
      workBranch: project.workBranch,
      token: tokenDescriptor(project),
      cloned: status !== null,
      ...(status ?? {}),
    });
  } catch (error) {
    return NextResponse.json(
      { error: redact(error instanceof Error ? error.message : String(error)) },
      { status: 500 },
    );
  }
}

type Action = "prepare" | "commit" | "push";

/**
 * Workspace actions. `prepare` clones or fetches; `commit` snapshots whatever
 * the agents changed; `push` sends the work branch to the remote.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });
  if (project.source !== "git" || !project.repoUrl) {
    return NextResponse.json({ error: "Not a git-backed project." }, { status: 400 });
  }

  let body: { action?: Action; message?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  try {
    switch (body.action) {
      case "prepare": {
        const dir = await prepareProject(project);
        return NextResponse.json({ ok: true, targetDir: dir });
      }
      case "commit": {
        const sha = await commitAll(
          project.targetDir,
          body.message?.trim() || "Mission Control: apply planned tasks",
        );
        return NextResponse.json({ ok: true, sha, committed: sha !== null });
      }
      case "push": {
        await pushBranch(
          project.targetDir,
          project.repoUrl,
          project.workBranch ?? "mission-control/work",
          resolveGitToken(project).token,
        );
        return NextResponse.json({ ok: true, branch: project.workBranch });
      }
      default:
        return NextResponse.json({ error: "Unknown action." }, { status: 400 });
    }
  } catch (error) {
    return NextResponse.json(
      { error: redact(error instanceof Error ? error.message : String(error)) },
      { status: 500 },
    );
  }
}
