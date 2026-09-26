import { currentLocale, translate } from "@/lib/i18n";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "pit.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {}
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {}
  },
};

type Options = Omit<RequestInit, "body"> & { json?: unknown; body?: BodyInit };

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const { json, ...init } = options;
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  headers.set("Accept-Language", currentLocale()); // the API answers errors in this language
  let body = init.body;
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1${path}`, { ...init, headers, body });
  } catch {
    throw new ApiError(0, "network", translate(currentLocale(), "Server bilan aloqa yo'q. Internetni tekshiring."));
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token) {
      tokenStore.clear();
      window.dispatchEvent(new Event("pit:logout"));
    }
    throw new ApiError(response.status, data?.code ?? "error", data?.message ?? translate(currentLocale(), "Kutilmagan xatolik yuz berdi"));
  }
  return data as T;
}

export const fetcher = <T>(path: string) => api<T>(path);

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : translate(currentLocale(), "Kutilmagan xatolik yuz berdi");
}
