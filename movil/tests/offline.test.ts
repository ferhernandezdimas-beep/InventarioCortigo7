import test from "node:test";
import assert from "node:assert/strict";
import {
  assistant,
  cartTotal,
  decimalInput,
  effectiveInventory,
  mayDiscard,
  saleCommand,
} from "../src/domain";
import { flushQueue } from "../src/sync";
import type { Snapshot, QueueItem } from "../src/types";

const snapshot: Snapshot = {
  schema_version: 1,
  server_time: "2026-11-15T12:00:00Z",
  user: {
    id: 1,
    name: "Responsable",
    email: "user@example.com",
    role: "admin",
    role_label: "Administrador",
    permissions: ["sales.read", "inventory.read"],
  },
  expiry_alert_days: 7,
  ingredients: [
    {
      id: 1,
      name: "Jitomate saladet",
      code: "VER-01",
      category: "Verduras",
      unit: "kg",
      minimum: "2.000000",
      maximum: "8.000000",
      physical: "5.000000",
      available: "5.000000",
      known_value: "100.00",
      unknown: "0",
      supplier_id: 1,
    },
  ],
  lots: [
    {
      id: 1,
      ingredient_id: 1,
      code: "L01",
      quantity: "3.000000",
      expires_on: "2026-11-14",
      received_at: "2026-11-10T12:00:00Z",
    },
    {
      id: 2,
      ingredient_id: 1,
      code: "L02",
      quantity: "2.000000",
      expires_on: "2026-11-20",
      received_at: "2026-11-12T12:00:00Z",
    },
  ],
  suppliers: [{ id: 1, name: "Huerta del Bajío" }],
  presentations: [],
  products: [
    {
      id: 1,
      name: "Ensalada de temporada",
      price: "0.10",
      category: "Cocina",
      code: null,
      recipe_version: 3,
      requirements: [{ ingredient_id: 1, quantity: "0.25" }],
    },
  ],
  operations: [],
  sales: [],
};
const now = new Date("2026-11-15T20:00:00Z");
const item = (key = "key-1"): QueueItem => ({
  key,
  command: {
    key,
    kind: "issue",
    reason: "Cocina",
    lines: [{ ingredient_id: 1, quantity: "1.000000" }],
  },
  label: "Salida",
  created_at: "2026-11-15T20:00:00Z",
  status: "pending",
  attempted: false,
  result_id: null,
  error: null,
});

test("decimal quantities and money do not use binary arithmetic", () => {
  assert.equal(decimalInput("1,2345"), "1.234500");
  assert.equal(cartTotal(snapshot.products, { 1: 3 }), "0.30");
  assert.throws(() => decimalInput("1.0000001"));
  assert.throws(() => decimalInput("-1"));
  assert.throws(() => decimalInput("NaN"));
});
test("expired lots stop counting when the phone has not synchronized overnight", () => {
  assert.equal(effectiveInventory(snapshot, now)[0].available, "2.000000");
  assert.equal(
    effectiveInventory(snapshot, new Date("2026-11-21T20:00:00Z"))[0].available,
    "0.000000",
  );
});
test("offline sale freezes prices and recipe versions", () => {
  const command = saleCommand(
    "sale-1",
    snapshot.products,
    { 1: 3 },
    "cash",
    "1",
  );
  assert.equal(command.kind, "sale");
  if (command.kind !== "sale") throw new Error();
  assert.equal(command.expected_total, "0.30");
  assert.deepEqual(command.expected_recipes, { "1": 3 });
  assert.throws(() =>
    saleCommand("sale-2", snapshot.products, { 1: 3 }, "cash", "0.20"),
  );
});
test("assistant calculates replenishment, flags expiry and never sums shared capacity", () => {
  assert.match(
    assistant("qué debo comprar", snapshot, [], now).text,
    /reponer 6 kg/,
  );
  assert.match(assistant("qué caduca", snapshot, [], now).text, /CADUCADO/);
  assert.match(
    assistant("qué puedo preparar", snapshot, [], now).text,
    /8 porciones/,
  );
  assert.match(
    assistant("qué puedo preparar", snapshot, [], now).text,
    /independiente/,
  );
  assert.match(
    assistant("jitomate", snapshot, [], now).text,
    /Disponible: 2 kg/,
  );
});
test("unknown outcomes cannot be discarded and retry keeps identical payload", async () => {
  const original = item();
  let saved = original;
  await assert.rejects(
    flushQueue([original], {
      save: async (value) => {
        saved = JSON.parse(JSON.stringify(value));
      },
      send: async () => {
        throw new Error("Connection lost after commit");
      },
      status: () => 0,
    }),
  );
  assert.equal(saved.attempted, true);
  assert.equal(saved.status, "pending");
  assert.equal(mayDiscard(saved), false);
  let received: QueueItem | null = null;
  await flushQueue([saved], {
    save: async (value) => {
      saved = value;
    },
    send: async (value) => {
      received = value;
      return { id: "original-server-folio" };
    },
    status: () => 0,
  });
  assert.deepEqual(
    (received as unknown as QueueItem).command,
    original.command,
  );
  assert.equal(saved.result_id, "original-server-folio");
  assert.equal(saved.status, "confirmed");
});
test("a lost acknowledgement after commit is replayed after restart", async () => {
  let disk = item();
  let writes = 0;
  let requests = 0;
  const send = async () => {
    requests++;
    return { id: "same-folio" };
  };
  await assert.rejects(
    flushQueue([disk], {
      save: async (value) => {
        if (++writes === 2) throw new Error("App stopped");
        disk = value;
      },
      send,
      status: () => 0,
    }),
  );
  assert.equal(disk.status, "pending");
  await flushQueue([JSON.parse(JSON.stringify(disk))], {
    save: async (value) => {
      disk = value;
    },
    send,
    status: () => 0,
  });
  assert.equal(requests, 2);
  assert.equal(disk.result_id, "same-folio");
});
test("conflicts stop subsequent operations and remain explicitly reviewable", async () => {
  const saved: QueueItem[] = [];
  let sent = 0;
  await assert.rejects(
    flushQueue([item("one"), item("two")], {
      save: async (v) => {
        saved.push(v);
      },
      send: async () => {
        sent++;
        throw Object.assign(new Error("Stock unavailable"), { status: 422 });
      },
      status: (e) => (e as { status: number }).status,
    }),
  );
  assert.equal(sent, 1);
  assert.equal(saved.at(-1)?.status, "conflict");
  assert.equal(mayDiscard(saved.at(-1)!), true);
  await flushQueue([saved.at(-1)!, item("two")], {
    save: async () => {},
    send: async () => {
      throw new Error("must not send");
    },
    status: () => 0,
  });
});
test("busy, unauthenticated and unavailable responses remain retryable", async () => {
  for (const status of [401, 403, 409, 429, 500, 503]) {
    let saved = item();
    await assert.rejects(
      flushQueue([saved], {
        save: async (value) => {
          saved = value;
        },
        send: async () => {
          throw new Error("busy");
        },
        status: () => status,
      }),
    );
    assert.equal(saved.status, "pending");
    assert.equal(mayDiscard(saved), false);
  }
});
test("confirmed operations are never sent again", async () => {
  await flushQueue([{ ...item(), status: "confirmed" }], {
    save: async () => {
      throw new Error("must not write");
    },
    send: async () => {
      throw new Error("must not send");
    },
    status: () => 0,
  });
});
