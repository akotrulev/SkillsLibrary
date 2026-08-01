import { EventEmitter } from "node:events";
import type { RunEvent } from "./types";

/**
 * Process-local pub/sub bridging the orchestrator to SSE subscribers.
 *
 * Mission Control is a single-process local tool, so an in-memory emitter is
 * sufficient; there is no cross-instance fan-out to worry about.
 */
class RunEventBus extends EventEmitter {
  constructor() {
    super();
    // A board with many open task cards can exceed the default 10 listeners.
    this.setMaxListeners(200);
  }

  publish(runId: string, event: RunEvent): void {
    this.emit(runId, event);
  }

  subscribe(runId: string, listener: (event: RunEvent) => void): () => void {
    this.on(runId, listener);
    return () => {
      this.off(runId, listener);
    };
  }
}

/**
 * Survives Next.js dev-server hot reloads, which would otherwise create a new
 * bus per module evaluation and silently drop live task updates.
 */
const globalForBus = globalThis as unknown as { __mcEventBus?: RunEventBus };

export const eventBus = globalForBus.__mcEventBus ?? new RunEventBus();
if (!globalForBus.__mcEventBus) globalForBus.__mcEventBus = eventBus;
