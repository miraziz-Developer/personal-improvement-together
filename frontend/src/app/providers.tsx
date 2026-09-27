"use client";

import { useEffect, useRef } from "react";
import { SWRConfig, useSWRConfig } from "swr";

import { ToastProvider } from "@/components/toast";
import { fetcher } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

/** Server texts (catalog, badges, region names) follow Accept-Language, so switching the
 * language refetches everything already on screen. */
function RefetchOnLanguageChange() {
  const { locale } = useI18n();
  const { mutate } = useSWRConfig();
  const previous = useRef(locale);
  useEffect(() => {
    document.documentElement.lang = locale;
    if (previous.current === locale) return;
    previous.current = locale;
    mutate(() => true);
  }, [locale, mutate]);
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig value={{ fetcher, revalidateOnFocus: true, shouldRetryOnError: false }}>
      <RefetchOnLanguageChange />
      <ToastProvider>
        <AuthProvider>{children}</AuthProvider>
      </ToastProvider>
    </SWRConfig>
  );
}
