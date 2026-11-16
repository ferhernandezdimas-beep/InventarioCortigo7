import type { QueueItem } from "./types";

export type SyncPorts = {
  save: (item: QueueItem) => Promise<void>;
  send: (item: QueueItem, recover: boolean) => Promise<{ id: string }>;
  status: (error: unknown) => number;
};
/** FIFO, durable attempts and acknowledgements; interrupted attempts retain key/body. */
export async function flushQueue(items: QueueItem[], ports: SyncPorts) {
  for (const original of items) {
    if (original.status === "confirmed") continue;
    if (original.status === "conflict") break;
    const attempted = { ...original, attempted: true, error: null };
    await ports.save(attempted);
    let result: { id: string };
    try {
      result = await ports.send(attempted, original.attempted);
    } catch (error) {
      const status = ports.status(error);
      const conflict = status === 422;
      await ports.save({
        ...attempted,
        status: conflict ? "conflict" : "pending",
        error:
          error instanceof Error ? error.message : "No se pudo sincronizar.",
      });
      throw error;
    }
    // An interrupted acknowledgement write is safe: the next attempt replays on the server.
    await ports.save({
      ...attempted,
      status: "confirmed",
      result_id: result.id,
      error: null,
    });
  }
}
