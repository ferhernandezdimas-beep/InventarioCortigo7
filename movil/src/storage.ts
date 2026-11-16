import * as SQLite from "expo-sqlite";
import * as SecureStore from "expo-secure-store";
import * as Crypto from "expo-crypto";
import { SERVER } from "./api";
import { mayDiscard } from "./domain";
import { SCHEMA, READ_QUEUE } from "./schema";
import type { Session, Snapshot, QueueItem } from "./types";

const SESSION_KEY = "cortijo7.mobile.session.v1";
let connection: SQLite.SQLiteDatabase | null = null;
export async function readSession(): Promise<Session | null> {
  const raw = await SecureStore.getItemAsync(SESSION_KEY);
  if (!raw) return null;
  try {
    const value = JSON.parse(raw);
    const session = value.session;
    return value.server === SERVER &&
      typeof session?.token === "string" &&
      Number.isInteger(session?.user?.id) &&
      Number.isFinite(Date.parse(session?.expires_at))
      ? session
      : null;
  } catch {
    return null;
  }
}
export async function writeSession(session: Session) {
  await SecureStore.setItemAsync(
    SESSION_KEY,
    JSON.stringify({ server: SERVER, session }),
    { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY },
  );
}
export async function openStorage(userId: number) {
  if (connection) await connection.closeAsync();
  const owner = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    `${SERVER}/${userId}`,
  );
  connection = await SQLite.openDatabaseAsync(
    `cortijo7-${owner.slice(0, 24)}.db`,
  );
  await connection.execAsync(SCHEMA);
}
function db() {
  if (!connection) throw new Error("El almacenamiento no está listo.");
  return connection;
}
export async function readCache(): Promise<Snapshot | null> {
  const row = await db().getFirstAsync<{ payload: string }>(
    "SELECT payload FROM cache WHERE id=1",
  );
  return row ? JSON.parse(row.payload) : null;
}
export async function saveCache(snapshot: Snapshot) {
  await db().runAsync(
    "INSERT INTO cache (id,payload) VALUES (1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
    JSON.stringify(snapshot),
  );
}
export async function readQueue(): Promise<QueueItem[]> {
  const rows = await db().getAllAsync<{ payload: string }>(READ_QUEUE);
  return rows.map((r) => JSON.parse(r.payload));
}
export async function saveQueueItem(item: QueueItem) {
  await db().runAsync(
    "INSERT INTO outbox (key,payload,created_at) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload",
    item.key,
    JSON.stringify(item),
    item.created_at,
  );
}
export async function addQueueItem(item: QueueItem) {
  await db().runAsync(
    "INSERT INTO outbox (key,payload,created_at) VALUES (?,?,?)",
    item.key,
    JSON.stringify(item),
    item.created_at,
  );
}
export async function discardQueueItem(item: QueueItem) {
  if (!mayDiscard(item))
    throw new Error(
      "El resultado aún es incierto. Reintenta la misma referencia antes de descartarla.",
    );
  await db().runAsync("DELETE FROM outbox WHERE key=?", item.key);
}
export async function clearLocalSession() {
  const pending = (await readQueue()).some((i) => i.status !== "confirmed");
  if (pending)
    throw new Error(
      "Resuelve tus operaciones pendientes antes de cerrar sesión.",
    );
  await db().withExclusiveTransactionAsync(async (tx) => {
    await tx.execAsync("DELETE FROM cache; DELETE FROM outbox;");
  });
  await SecureStore.deleteItemAsync(SESSION_KEY);
}
