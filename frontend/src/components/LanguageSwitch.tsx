"use client";

import clsx from "clsx";

import { LOCALES, storeLocale, useI18n } from "@/lib/i18n";

/** UZ | RU. The choice is remembered on this device and, once signed in, on the account
 * (so the coach and the Telegram bot switch too — see AuthProvider). */
export function LanguageSwitch({ className }: { className?: string }) {
  const { locale } = useI18n();
  return (
    <div role="group" aria-label="Til / Язык" className={clsx("inline-flex rounded-xl bg-white/5 p-0.5 text-xs font-semibold", className)}>
      {LOCALES.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => storeLocale(value)}
          aria-pressed={locale === value}
          title={label}
          className={clsx(
            "rounded-lg px-2.5 py-1 uppercase transition",
            locale === value ? "bg-white/15 text-white" : "text-mist hover:text-white",
          )}
        >
          {value}
        </button>
      ))}
    </div>
  );
}
