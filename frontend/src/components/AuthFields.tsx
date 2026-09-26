"use client";

import Link from "next/link";
import useSWR from "swr";

import type { Region } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

export function RegionSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const { data: regions } = useSWR<Region[]>("/regions");
  const { locale, t } = useI18n();
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      required
      className="h-12 w-full rounded-2xl border border-white/10 bg-ink-900/70 px-4 text-white outline-none focus:border-flame-500/70"
    >
      <option value="" disabled>
        {t("Tanlang")}
      </option>
      {regions?.map((r) => (
        <option key={r.id} value={r.id}>
          {locale === "ru" ? r.name_ru : r.name_uz}
        </option>
      ))}
    </select>
  );
}

export function TermsConsent({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  // The sentence is built differently in each language (Russian needs another case around the
  // links), so it is assembled here rather than from single dictionary entries.
  const { locale } = useI18n();
  const ru = locale === "ru";
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.02] p-4 text-sm leading-relaxed text-white/85">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        required
        className="mt-0.5 size-5 shrink-0 accent-flame-500"
      />
      <span>
        {ru && "Я ознакомлен(а) с "}
        <Link href="/terms" target="_blank" className="font-semibold text-flame-400 underline">
          {ru ? "Условиями использования" : "Foydalanish shartlari"}
        </Link>{" "}
        {ru ? "и" : "va"}{" "}
        <Link href="/privacy" target="_blank" className="font-semibold text-flame-400 underline">
          {ru ? "Политикой конфиденциальности" : "Maxfiylik siyosati"}
        </Link>{" "}
        {ru
          ? "и согласен(на). Если мне нет 18 — согласен мой родитель или опекун."
          : "bilan tanishdim va roziman. 18 yoshgacha bo'lsam — ota-onam yoki vasiyim rozi."}
      </span>
    </label>
  );
}

export function OrDivider() {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-3 text-sm text-mist">
      <span className="h-px flex-1 bg-white/10" />
      {t("yoki")}
      <span className="h-px flex-1 bg-white/10" />
    </div>
  );
}
