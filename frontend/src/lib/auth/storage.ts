/**
 * A tiny key-value store on IndexedDB, for what must survive a reload: the device key pair (a
 * non-extractable `CryptoKey`, which only IndexedDB can keep) and the refresh token.
 *
 * Without IndexedDB (tests, private modes that block it) it falls back to memory: the session
 * then lasts until the page is closed, which is safe.
 */

const DB_NAME = "vuelos-auth";
const STORE = "kv";

const memory = new Map<string, unknown>();
let database: Promise<IDBDatabase | null> | null = null;

function open(): Promise<IDBDatabase | null> {
  if (database) return database;
  database = new Promise((resolve) => {
    if (typeof indexedDB === "undefined") return resolve(null);
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(null);
  });
  return database;
}

function run<T>(db: IDBDatabase, mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>) {
  return new Promise<T>((resolve, reject) => {
    const request = action(db.transaction(STORE, mode).objectStore(STORE));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function readValue<T>(key: string): Promise<T | undefined> {
  const db = await open();
  if (!db) return memory.get(key) as T | undefined;
  return (await run(db, "readonly", (store) => store.get(key))) as T | undefined;
}

export async function writeValue(key: string, value: unknown): Promise<void> {
  const db = await open();
  if (!db) {
    memory.set(key, value);
    return;
  }
  await run(db, "readwrite", (store) => store.put(value, key));
}

export async function deleteValue(key: string): Promise<void> {
  const db = await open();
  if (!db) {
    memory.delete(key);
    return;
  }
  await run(db, "readwrite", (store) => store.delete(key));
}

/** Empties the in-memory store (tests run without IndexedDB). */
export function clearMemoryStorage(): void {
  memory.clear();
}
