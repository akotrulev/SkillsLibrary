import { NextResponse } from "next/server";
import { eventBus } from "@/lib/events";
import { updateRun } from "@/lib/store";

export const dynamic = "force-dynamic";

/**
 * Record answers to open questions. Answering unblocks any task the question
 * was gating; the run must then be started again to pick those tasks up.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;

  let body: { answers?: { questionId: string; optionId?: string; text?: string }[] };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const answers = body.answers ?? [];
  if (answers.length === 0) {
    return NextResponse.json({ error: "No answers supplied." }, { status: 400 });
  }

  const run = await updateRun(runId, (r) => {
    const now = new Date().toISOString();
    for (const answer of answers) {
      const question = r.openQuestions.find((q) => q.id === answer.questionId);
      if (!question) continue;

      const option = question.options.find((o) => o.id === answer.optionId);
      const text = answer.text?.trim() || option?.label;
      if (!text) continue;

      question.answer = { optionId: option?.id, text, answeredAt: now };

      // Release tasks this question was holding.
      for (const taskId of question.blocksTaskIds) {
        const task = r.tasks.find((t) => t.id === taskId);
        if (task && task.status === "blocked" && !task.error) task.status = "ready";
      }
    }

    const stillBlocking = r.openQuestions.some(
      (q) => !q.answer && q.blocksTaskIds.length > 0,
    );
    if (r.status === "paused" && !stillBlocking) r.status = "planned";
  });

  if (!run) return NextResponse.json({ error: "Run not found." }, { status: 404 });

  eventBus.publish(runId, { type: "run:updated", run });
  return NextResponse.json(run);
}
