import type { Session, Snapshot, Command } from "./types";

export const SERVER = (
  process.env.EXPO_PUBLIC_API_URL || "https://cortijo7.onrender.com"
).replace(/\/$/, "");
if (
  !SERVER.startsWith("https://") &&
  !(
    __DEV__ && /^http:\/\/(localhost|127\.0\.0\.1|192\.168\.|10\.)/.test(SERVER)
  )
)
  throw new Error("Configura una URL HTTPS para el servidor.");
const BASE = SERVER + "/api/mobile/v1";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code: string,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  token?: string,
  data?: unknown,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(BASE + path, {
      method: data === undefined ? "GET" : "POST",
      signal: controller.signal,
      credentials: "omit",
      headers: {
        Accept: "application/json",
        ...(data !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: "Bearer " + token } : {}),
      },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
    const result = await response.json().catch(() => null);
    if (!response.ok)
      throw new ApiError(
        result?.error?.message ||
          "El servidor no pudo responder. Conservamos tus pendientes.",
        response.status,
        result?.error?.code || "unavailable",
      );
    if (!result) throw new Error("Respuesta incompleta. Vuelve a sincronizar.");
    return result as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new Error(
      "No pudimos conectar con Render. Tus datos y pendientes siguen en este teléfono. El servicio gratuito puede tardar en despertar.",
    );
  } finally {
    clearTimeout(timer);
  }
}
export const signIn = (email: string, password: string, device_name: string) =>
  request<Session>("/auth/login", undefined, { email, password, device_name });
export const download = (token: string) =>
  request<Snapshot>("/snapshot", token);
export async function upload(token: string, command: Command, recover = false) {
  if (recover) {
    try {
      return await request<{ id: string; key: string; status: "confirmed" }>(
        "/operations/" + command.key,
        token,
      );
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 404) throw error;
    }
  }
  return request<{ id: string; key: string; status: "confirmed" }>(
    "/operations",
    token,
    command,
  );
}
