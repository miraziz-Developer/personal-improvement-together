"use client";

import { Fragment, useCallback, useSyncExternalStore, type ReactNode } from "react";

import { RU } from "@/lib/ru";

// The interface is written in Uzbek; the Uzbek sentence is the key, other languages map it.
// A sentence missing from a dictionary shows in Uzbek rather than breaking the page.
export type Locale = "uz" | "ru";
export const LOCALES: { value: Locale; label: string }[] = [
  { value: "uz", label: "O'zbekcha" },
  { value: "ru", label: "Русский" },
];

const KEY = "pit.locale";
const EVENT = "pit:locale";
const DICTIONARIES: Record<Locale, Record<string, string>> = { uz: {}, ru: RU };

function read(): Locale {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored === "uz" || stored === "ru") return stored;
  } catch {}
  return navigator.language?.toLowerCase().startsWith("ru") ? "ru" : "uz";
}

function subscribe(callback: () => void) {
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

/** The current language outside React (the API client sends it as Accept-Language). */
export function currentLocale(): Locale {
  return typeof window === "undefined" ? "uz" : read();
}

export function storeLocale(locale: Locale) {
  try {
    localStorage.setItem(KEY, locale);
  } catch {}
  document.documentElement.lang = locale;
  window.dispatchEvent(new Event(EVENT));
}

export function translate(locale: Locale, text: string, values?: Record<string, string | number>): string {
  const template = DICTIONARIES[locale][text] ?? text;
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in values ? String(values[name]) : match));
}

/** Like translate(), but placeholders may be React elements (a highlighted name, a link). */
export function translateNodes(locale: Locale, text: string, nodes: Record<string, ReactNode>): ReactNode {
  const template = DICTIONARIES[locale][text] ?? text;
  return template.split(/(\{\w+\})/).map((part, index) => {
    const name = part.match(/^\{(\w+)\}$/)?.[1];
    return <Fragment key={index}>{name && name in nodes ? nodes[name] : part}</Fragment>;
  });
}

export function useI18n() {
  const locale = useSyncExternalStore(subscribe, read, () => "uz" as Locale);
  const t = useCallback(
    (text: string, values?: Record<string, string | number>) => translate(locale, text, values),
    [locale],
  );
  const tx = useCallback(
    (text: string, nodes: Record<string, ReactNode>) => translateNodes(locale, text, nodes),
    [locale],
  );
  return { locale, t, tx };
}
