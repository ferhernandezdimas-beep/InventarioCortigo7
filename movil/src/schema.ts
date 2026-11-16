// Local-only schema, shared by Expo SQLite and the persistence protocol tests.
export const SCHEMA = `PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS cache (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (key TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
PRAGMA user_version = 1;`;
export const READ_QUEUE =
  "SELECT payload FROM outbox ORDER BY created_at,rowid";
