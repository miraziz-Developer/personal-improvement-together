"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore } from "react";
import useSWR, { type KeyedMutator } from "swr";

import { api, tokenStore } from "./api";
import { useI18n } from "./i18n";
import type { Me } from "./types";

interface AuthState {
  ready: boolean;
  token: string | null;
  me: Me | undefined;
  refreshMe: KeyedMutator<Me>;
  signIn: (token: string) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

// The token lives in localStorage; React subscribes to it as an external store, so every tab
// and every 401 (api.ts dispatches "pit:logout") updates the UI without extra effects.
const listeners = new Set<() => void>();
function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  window.addEventListener("pit:logout", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
    window.removeEventListener("pit:logout", listener);
  };
}
const notify = () => listeners.forEach((listener) => listener());

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = useSyncExternalStore(subscribe, tokenStore.get, () => null);
  const ready = useSyncExternalStore(subscribe, () => true, () => false);
  const { data: me, mutate } = useSWR<Me>(token ? "/me" : null, { refreshInterval: 60_000 });
  const { locale } = useI18n();

  // The interface language is the truth; the server follows it so the coach and the bot speak
  // the same language as the site.
  useEffect(() => {
    if (me && me.locale !== locale) {
      api("/me/locale", { method: "PUT", json: { locale } })
        .then(() => mutate())
        .catch(() => {});
    }
  }, [me, locale, mutate]);

  const signIn = useCallback((value: string) => {
    tokenStore.set(value);
    notify();
  }, []);

  const signOut = useCallback(() => {
    tokenStore.clear();
    notify();
    router.replace("/");
  }, [router]);

  const value = useMemo(
    () => ({ ready, token, me, refreshMe: mutate, signIn, signOut }),
    [ready, token, me, mutate, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

/** Server-side feature switches. Paid (stake) mode stays hidden until it is turned on. */
export function useFeatures() {
  const { data } = useSWR<{
    stakes_enabled: boolean;
    terms_version: string;
    telegram_bot: string | null;
    google_client_id: string | null;
    sms_enabled: boolean;
    push_public_key: string | null;
  }>("/features", { revalidateOnFocus: false });
  return {
    stakesEnabled: data?.stakes_enabled ?? false,
    termsVersion: data?.terms_version ?? "",
    telegramBot: data?.telegram_bot ?? null,
    googleClientId: data?.google_client_id ?? null,
    smsEnabled: data?.sms_enabled ?? false,
    pushPublicKey: data?.push_public_key ?? null,
  };
}

/** A `?next=` target from the URL, only if it stays on this site ("//evil.com" does not). */
export function safeNext(value: string | null | undefined): string | null {
  return value && value.startsWith("/") && !value.startsWith("//") && !value.startsWith("/\\") ? value : null;
}
