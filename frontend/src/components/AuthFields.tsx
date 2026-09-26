"use client";

import Link from "next/link";
import useSWR from "swr";

import type { Region } from "@/lib/types";

export function RegionSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const { data: regions } = useSWR<Region[]>("/regions");
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      required
      className="h-12 w-full rounded-2xl border border-white/10 bg-ink-900/70 px-4 text-white outline-none focus:border-flame-500/70"
    >
      <option value="" disabled>
        Tanlang
      </option>
      {regions?.map((r) => (
        <option key={r.id} value={r.id}>
          {r.name_uz}
        </option>
      ))}
    </select>
  );
}

export function TermsConsent({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
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
        <Link href="/terms" target="_blank" className="font-semibold text-flame-400 underline">
          Foydalanish shartlari
        </Link>{" "}
        va{" "}
        <Link href="/privacy" target="_blank" className="font-semibold text-flame-400 underline">
          Maxfiylik siyosati
        </Link>{" "}
        bilan tanishdim va roziman. 18 yoshgacha bo'lsam — ota-onam yoki vasiyim rozi.
      </span>
    </label>
  );
}

export function OrDivider() {
  return (
    <div className="flex items-center gap-3 text-sm text-mist">
      <span className="h-px flex-1 bg-white/10" />
      yoki
      <span className="h-px flex-1 bg-white/10" />
    </div>
  );
}
