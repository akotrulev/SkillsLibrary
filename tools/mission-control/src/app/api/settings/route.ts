import { NextResponse } from "next/server";
import { redact } from "@/lib/git";
import {
  ANTHROPIC_ENV_NAMES,
  setCredential,
  setPreferences,
  settingsView,
  type AnthropicEnvName,
} from "@/lib/settings";

export const dynamic = "force-dynamic";

/**
 * Instance settings.
 *
 * Credentials are **write-only across this API**, exactly as the per-project
 * token route is: they go in on PUT and no route returns one. GET answers with
 * state — where the effective value comes from, a last-four hint, and what the
 * host offers underneath.
 */

export async function GET() {
  return NextResponse.json(await settingsView());
}

interface PutBody {
  /** A credential value, or null to clear it and fall back to the host. */
  anthropicCredential?: string | null;
  /** Which variable the Anthropic credential becomes. */
  anthropicEnvName?: AnthropicEnvName;
  githubToken?: string | null;
  plannerModel?: string | null;
  implementerModel?: string | null;
  maxParallel?: number | null;
  anthropicBaseUrl?: string | null;
}

export async function PUT(request: Request) {
  let body: PutBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (
    body.anthropicEnvName !== undefined &&
    !ANTHROPIC_ENV_NAMES.includes(body.anthropicEnvName)
  ) {
    return NextResponse.json(
      { error: `Unsupported variable. Expected one of: ${ANTHROPIC_ENV_NAMES.join(", ")}` },
      { status: 400 },
    );
  }

  try {
    // Each key is applied only when present, so the panel can save one field.
    if (body.anthropicCredential !== undefined) {
      await setCredential("anthropic", body.anthropicCredential, body.anthropicEnvName);
    }
    if (body.githubToken !== undefined) {
      await setCredential("github", body.githubToken);
    }
    await setPreferences({
      plannerModel: body.plannerModel,
      implementerModel: body.implementerModel,
      maxParallel: body.maxParallel,
      anthropicBaseUrl: body.anthropicBaseUrl,
    });

    return NextResponse.json(await settingsView());
  } catch (error) {
    // `redact` in case a value ever reaches an error string.
    return NextResponse.json(
      {
        error: redact(
          error instanceof Error ? error.message : "Could not save settings.",
        ),
      },
      { status: 500 },
    );
  }
}
