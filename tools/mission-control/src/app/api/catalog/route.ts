import { NextResponse } from "next/server";
import { getCatalog } from "@/lib/catalog";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function GET(request: Request) {
  const force = new URL(request.url).searchParams.get("refresh") === "1";
  try {
    const catalog = await getCatalog(force);
    return NextResponse.json({
      libraryRoot: catalog.libraryRoot,
      indexedAt: catalog.indexedAt,
      agentCount: catalog.agents.length,
      skillCount: catalog.skills.length,
      candidateCount: catalog.candidateCount,
      unreadable: catalog.unreadable,
      malformed: catalog.malformed,
      agents: catalog.agents.map((a) => ({
        name: a.name,
        domain: a.domain,
        description: a.description,
        relPath: a.relPath,
      })),
      skills: catalog.skills.map((s) => ({
        name: s.name,
        domain: s.domain,
        relPath: s.relPath,
      })),
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to index catalog." },
      { status: 500 },
    );
  }
}
