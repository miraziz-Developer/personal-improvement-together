"use client";

import type { ReactNode } from "react";

import { useI18n } from "@/lib/i18n";

/** Legal texts are whole documents per language rather than dictionary sentences — a lawyer
 * reads them as a unit, and word-by-word keys would fall apart on the first rewrite. */
export function Localized({ uz, ru }: { uz: ReactNode; ru: ReactNode }) {
  const { locale } = useI18n();
  return <>{locale === "ru" ? ru : uz}</>;
}
