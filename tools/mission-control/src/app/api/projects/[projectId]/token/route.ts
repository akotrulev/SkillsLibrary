import { NextResponse } from "next/server";
import { checkAccess, redact } from "@/lib/git";
import { getProject, resolveGitToken, setProjectToken, tokenDescriptor } from "@/lib/projects";
import { secretsEnabled } from "@/lib/secrets";

export const dynamic = "force-dynamic";

/**
 * Per-project GitHub credential.
 *
 * The token is write-only across this API: it goes in on PUT and is never
 * returned by any route. Clients get a descriptor — where the credential comes
 * from, a last-four hint, and whether pushing is possible.
 */

/** Current credential descriptor. Never includes the token itself. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });
  return NextResponse.json(tokenDescriptor(project));
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });

  if (!secretsEnabled()) {
    return NextResponse.json(
      {
        error:
          "MISSION_CONTROL_SECRET is not set, so tokens cannot be stored encrypted. Set it and restart, or use MISSION_CONTROL_GIT_TOKEN for all projects.",
      },
      { status: 409 },
    );
  }

  let body: { token?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const token = body.token?.trim();
  if (!token) {
    return NextResponse.json({ error: "A token is required." }, { status: 400 });
  }

  try {
    const updated = await setProjectToken(projectId, token);
    if (!updated) {
      return NextResponse.json({ error: "Project not found." }, { status: 404 });
    }
    return NextResponse.json(tokenDescriptor(updated));
  } catch (error) {
    return NextResponse.json(
      { error: redact(error instanceof Error ? error.message : "Could not store token.") },
      { status: 500 },
    );
  }
}

/** Remove the project token; resolution falls back to the environment. */
export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const updated = await setProjectToken(projectId, null);
  if (!updated) return NextResponse.json({ error: "Project not found." }, { status: 404 });
  return NextResponse.json(tokenDescriptor(updated));
}

/**
 * Verify the resolved credential actually reaches the repo, without cloning.
 * Accepts an optional candidate token so it can be tested before saving.
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

  let body: { token?: string } = {};
  try {
    body = await request.json();
  } catch {
    // No body is fine: test whatever is currently resolved.
  }

  const candidate = body.token?.trim();
  const token = candidate || resolveGitToken(project).token;
  const result = await checkAccess(project.repoUrl, token, project.targetDir);

  return NextResponse.json(
    result.ok
      ? {
          ok: true,
          verified: result.verified,
          testedWith: candidate ? "supplied" : tokenDescriptor(project).source,
        }
      : { ok: false, reason: result.reason },
  );
}
