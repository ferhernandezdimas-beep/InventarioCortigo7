import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { SCHEMA, READ_QUEUE } from "../src/schema";

test("SQLite local queue and snapshot survive closing and reopening the database", () => {
  const folder = mkdtempSync(join(tmpdir(), "c7-local-"));
  const path = join(folder, "device.db");
  try {
    let db = new DatabaseSync(path);
    db.exec(SCHEMA);
    db.prepare("INSERT INTO cache(id,payload) VALUES(1,?)").run(
      JSON.stringify({ server_time: "2026-11-15T20:00:00Z" }),
    );
    // Equal timestamps still preserve capture order, not lexical UUID order.
    const insert = db.prepare(
      "INSERT INTO outbox(key,payload,created_at) VALUES(?,?,?)",
    );
    insert.run(
      "z-first",
      JSON.stringify({ key: "z-first", status: "pending", attempted: true }),
      "2026-11-15T20:00:00Z",
    );
    insert.run(
      "a-second",
      JSON.stringify({ key: "a-second", status: "pending", attempted: false }),
      "2026-11-15T20:00:00Z",
    );
    db.close();
    db = new DatabaseSync(path);
    db.exec(SCHEMA);
    const rows = db
      .prepare(READ_QUEUE)
      .all()
      .map((r) => JSON.parse(r.payload as string));
    assert.deepEqual(
      rows.map((r) => r.key),
      ["z-first", "a-second"],
    );
    assert.equal(rows[0].attempted, true);
    assert.equal(
      JSON.parse(
        db.prepare("SELECT payload FROM cache WHERE id=1").get()!
          .payload as string,
      ).server_time,
      "2026-11-15T20:00:00Z",
    );
    assert.throws(() =>
      db
        .prepare("INSERT INTO outbox(key,payload,created_at) VALUES(?,?,?)")
        .run("z-first", "{}", "2026-11-15T20:00:00Z"),
    );
    db.close();
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});
