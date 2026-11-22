import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { AppState, Platform } from "react-native";
import * as Network from "expo-network";
import * as Crypto from "expo-crypto";
import type { Command, QueueItem, Session, Snapshot } from "./types";
import { ApiError, download, request, signIn, upload } from "./api";
import * as store from "./storage";
import { flushQueue } from "./sync";

type State = {
  ready: boolean;
  session: Session | null;
  snapshot: Snapshot | null;
  queue: QueueItem[];
  online: boolean;
  busy: boolean;
  needsLogin: boolean;
  message: string;
  login: (email: string, password: string) => Promise<void>;
  sync: () => Promise<void>;
  enqueue: (command: Command, label: string) => Promise<void>;
  discard: (item: QueueItem) => Promise<void>;
  logout: () => Promise<void>;
};
const Context = createContext<State | null>(null);
export const newKey = () => Crypto.randomUUID();
export function AppProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false),
    [session, setSession] = useState<Session | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null),
    [queue, setQueue] = useState<QueueItem[]>([]);
  const [online, setOnline] = useState(false),
    [busy, setBusy] = useState(false),
    [needsLogin, setNeedsLogin] = useState(false),
    [message, setMessage] = useState("");
  const sessionRef = useRef<Session | null>(null),
    lock = useRef(false),
    mounted = useRef(true);
  const setCurrent = (value: Session) => {
    sessionRef.current = value;
    setSession(value);
  };
  const sync = useCallback(async () => {
    const current = sessionRef.current;
    if (!current || lock.current) return;
    if (Date.now() >= Date.parse(current.expires_at)) {
      setNeedsLogin(true);
      return;
    }
    lock.current = true;
    setBusy(true);
    try {
      const network = await Network.getNetworkStateAsync();
      if (!network.isConnected || network.isInternetReachable === false)
        throw new Error(
          "Sin conexión. Puedes seguir consultando y capturando en el teléfono.",
        );
      await request("/auth/me", current.token); // Check current permissions and revocation before replay.
      let pushError: unknown;
      try {
        await flushQueue(await store.readQueue(), {
          save: store.saveQueueItem,
          send: (item, recover) => upload(current.token, item.command, recover),
          status: (error) => (error instanceof ApiError ? error.status : 0),
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) throw error;
        pushError = error;
      }
      const fresh = await download(current.token);
      if (
        fresh.schema_version !== 1 ||
        fresh.user.id !== current.user.id ||
        !Array.isArray(fresh.ingredients) ||
        !Array.isArray(fresh.products)
      )
        throw new Error(
          "El servidor requiere una actualización de la app. Conservamos tus datos.",
        );
      await store.saveCache(fresh);
      const updated = { ...current, user: fresh.user };
      await store.writeSession(updated);
      setCurrent(updated);
      setSnapshot(fresh);
      setNeedsLogin(false);
      const items = await store.readQueue();
      setQueue(items);
      setOnline(true);
      setMessage(
        pushError instanceof Error
          ? pushError.message
          : items.some((i) => i.status === "conflict")
            ? "Revisa el primer conflicto para continuar la sincronización."
            : "Todo al día con la web.",
      );
    } catch (error) {
      if (error instanceof ApiError && error.status === 401)
        setNeedsLogin(true);
      setMessage(
        error instanceof Error ? error.message : "No se pudo sincronizar.",
      );
      if (!(error instanceof ApiError)) setOnline(false);
      setQueue(await store.readQueue());
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }, []);
  useEffect(() => {
    mounted.current = true;
    (async () => {
      try {
        const cached = await store.readSession();
        if (cached) {
          await store.openStorage(cached.user.id);
          const [data, items] = await Promise.all([
            store.readCache(),
            store.readQueue(),
          ]);
          if (mounted.current) {
            setCurrent(cached);
            setSnapshot(data);
            setQueue(items);
            setNeedsLogin(Date.now() >= Date.parse(cached.expires_at));
          }
        }
      } catch {
        setMessage(
          "No se pudo abrir el almacenamiento. Reinicia la app sin desinstalarla.",
        );
      } finally {
        setReady(true);
      }
      void sync();
    })();
    const net = Network.addNetworkStateListener((state) => {
      setOnline(!!state.isConnected && state.isInternetReachable !== false);
      if (state.isConnected && state.isInternetReachable !== false) void sync();
    });
    const app = AppState.addEventListener("change", (state) => {
      if (state === "active") void sync();
    });
    const timer = setInterval(() => {
      if (AppState.currentState === "active") void sync();
    }, 60000);
    return () => {
      mounted.current = false;
      net.remove();
      app.remove();
      clearInterval(timer);
    };
  }, [sync]);
  const login = async (email: string, password: string) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    try {
      const fresh = await signIn(
        email.trim(),
        password,
        `Cortijo 7 · ${Platform.OS}`,
      );
      const old = sessionRef.current;
      if (
        old &&
        old.user.id !== fresh.user.id &&
        (await store.readQueue()).some((i) => i.status !== "confirmed")
      ) {
        await request("/auth/logout", fresh.token, {}).catch(() => {});
        throw new Error(
          "Este teléfono tiene operaciones de " +
            old.user.name +
            ". Inicia sesión con esa cuenta y resuélvelas antes de cambiar de usuario.",
        );
      }
      // Persist credentials before first download: a slow Render wake must not lose the session.
      await store.openStorage(fresh.user.id);
      await store.writeSession(fresh);
      setCurrent(fresh);
      setNeedsLogin(false);
      setSnapshot(await store.readCache());
      setQueue(await store.readQueue());
      const data = await download(fresh.token);
      if (data.schema_version !== 1 || data.user.id !== fresh.user.id)
        throw new Error("La respuesta del servidor no es compatible.");
      await store.saveCache(data);
      setSnapshot(data);
      setMessage("Bienvenido. Tus datos están disponibles sin conexión.");
      setOnline(true);
    } finally {
      lock.current = false;
      setBusy(false);
    }
    void sync();
  };
  const enqueue = async (command: Command, label: string) => {
    const current = sessionRef.current;
    if (
      !current ||
      !snapshot ||
      needsLogin ||
      Date.now() >= Date.parse(current.expires_at)
    )
      throw new Error("Vuelve a iniciar sesión antes de capturar.");
    const permission = command.kind.startsWith("catalog.")
      ? "catalog.write"
      : command.kind === "sale"
        ? "sales.write"
        : "inventory.write";
    if (!current.user.permissions.includes(permission))
      throw new Error("Tu cuenta no tiene permiso para esta operación.");
    const item: QueueItem = {
      key: command.key,
      command,
      label,
      created_at: new Date().toISOString(),
      status: "pending",
      attempted: false,
      error: null,
      result_id: null,
    };
    await store.addQueueItem(item);
    setQueue(await store.readQueue());
    setMessage("Guardado en este teléfono. Se confirmará al sincronizar.");
    void sync();
  };
  const discard = async (item: QueueItem) => {
    if (lock.current)
      throw new Error("Espera a que termine la sincronización.");
    await store.discardQueueItem(item);
    setQueue(await store.readQueue());
    void sync();
  };
  const logout = async () => {
    if (lock.current)
      throw new Error("Espera a que termine la sincronización.");
    if ((await store.readQueue()).some((i) => i.status !== "confirmed"))
      throw new Error(
        "Resuelve las operaciones pendientes antes de cerrar sesión.",
      );
    if (sessionRef.current)
      await request("/auth/logout", sessionRef.current.token, {});
    await store.clearLocalSession();
    sessionRef.current = null;
    setSession(null);
    setSnapshot(null);
    setQueue([]);
    setNeedsLogin(false);
  };
  return (
    <Context.Provider
      value={{
        ready,
        session,
        snapshot,
        queue,
        online,
        busy,
        needsLogin,
        message,
        login,
        sync,
        enqueue,
        discard,
        logout,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useApp() {
  const state = useContext(Context);
  if (!state) throw new Error("Missing AppProvider");
  return state;
}
