import { eventBus } from "@/lib/events";
import { loadRun } from "@/lib/store";
import type { RunEvent } from "@/lib/types";

export const dynamic = "force-dynamic";
export const maxDuration = 3600;

/**
 * SSE stream of run/task updates. The board opens this once per run and
 * applies deltas as agents work.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const run = await loadRun(runId);
  if (!run) return new Response("Run not found", { status: 404 });

  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      let closed = false;

      const send = (event: RunEvent) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
        } catch {
          closed = true;
        }
      };

      // Prime the client with current state so it never renders stale data.
      send({ type: "run:updated", run });

      const unsubscribe = eventBus.subscribe(runId, send);

      // Keep intermediaries from closing an idle connection.
      const heartbeat = setInterval(() => send({ type: "ping" }), 15_000);

      const close = () => {
        if (closed) return;
        closed = true;
        clearInterval(heartbeat);
        unsubscribe();
        try {
          controller.close();
        } catch {
          // Already closed.
        }
      };

      request.signal.addEventListener("abort", close);
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
