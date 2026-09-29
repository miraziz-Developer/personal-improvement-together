"use client";

import clsx from "clsx";
import { Trash2 } from "lucide-react";

import { Input, Label } from "@/components/ui";
import { WEEKDAYS_SHORT } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { awakeLongEnough, freeMinutes } from "@/lib/routine";
import type { BusyBlock } from "@/lib/types";

export type DayFrameValue = { wake: string; sleep: string; busy: BusyBlock[] };

const PRESETS: { label: string; block: BusyBlock }[] = [
  { label: "Ish: Du–Ju 09:00–18:00", block: { label: "Ish", weekdays: [0, 1, 2, 3, 4], start: "09:00", end: "18:00" } },
  { label: "O'qish: Du–Sha 08:00–13:00", block: { label: "O'qish", weekdays: [0, 1, 2, 3, 4, 5], start: "08:00", end: "13:00" } },
];

const hoursAndMinutes = (total: number) => `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;

/** What the server will accept: a real waking day and fully described commitments. */
export const frameIsValid = ({ wake, sleep, busy }: DayFrameValue) =>
  awakeLongEnough(wake, sleep) && busy.every((b) => b.label.trim() && b.weekdays.length > 0 && b.start < b.end);

/** Wake up, go to sleep, and the fixed commitments in between — with the free time it leaves. */
export function DayFrameEditor({ value, onChange }: { value: DayFrameValue; onChange: (value: DayFrameValue) => void }) {
  const { t } = useI18n();
  const { wake, sleep, busy } = value;
  const setWake = (next: string) => onChange({ ...value, wake: next });
  const setSleep = (next: string) => onChange({ ...value, sleep: next });
  const setBusy = (update: (all: BusyBlock[]) => BusyBlock[]) => onChange({ ...value, busy: update(busy) });
  const patchBlock = (index: number, changes: Partial<BusyBlock>) => setBusy((all) => all.map((b, i) => (i === index ? { ...b, ...changes } : b)));

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3">
        <label>
          <Label>{t("Uyg'onish")}</Label>
          <Input type="time" value={wake} onChange={(e) => setWake(e.target.value)} className="[color-scheme:dark]" />
        </label>
        <label>
          <Label>{t("Uxlash")}</Label>
          <Input type="time" value={sleep} onChange={(e) => setSleep(e.target.value)} className="[color-scheme:dark]" />
        </label>
      </div>

      <div>
        <Label hint={t("ish, o'qish, yo'l — reja bularni chetlab o'tadi")}>{t("Band vaqtlar")}</Label>
        <div className="flex flex-col gap-3">
          {busy.map((block, index) => (
            <div key={index} className="flex flex-col gap-2 rounded-2xl bg-ink-900/60 p-3">
              <div className="flex items-center gap-2">
                <input
                  value={block.label}
                  onChange={(e) => patchBlock(index, { label: e.target.value })}
                  maxLength={40}
                  autoFocus={!block.label}
                  placeholder={t("Nima qilasiz? Masalan: yo'l, sport zali")}
                  className="min-w-0 flex-1 bg-transparent px-1 text-sm font-semibold outline-none placeholder:font-normal placeholder:text-white/30"
                  aria-label={t("Nima qilasiz?")}
                />
                <input type="time" value={block.start} onChange={(e) => patchBlock(index, { start: e.target.value })} className="rounded-lg bg-white/5 px-2 py-1 text-sm tabular-nums [color-scheme:dark]" aria-label={t("Boshlanishi")} />
                <span className="text-mist">–</span>
                <input type="time" value={block.end} onChange={(e) => patchBlock(index, { end: e.target.value })} className="rounded-lg bg-white/5 px-2 py-1 text-sm tabular-nums [color-scheme:dark]" aria-label={t("Tugashi")} />
                <button onClick={() => setBusy((all) => all.filter((_, i) => i !== index))} className="p-1 text-mist hover:text-danger" aria-label={t("O'chirish")}>
                  <Trash2 className="size-4" />
                </button>
              </div>
              <div className="flex gap-1">
                {WEEKDAYS_SHORT.map((day, weekday) => {
                  const on = block.weekdays.includes(weekday);
                  return (
                    <button
                      key={day}
                      onClick={() => patchBlock(index, { weekdays: on ? block.weekdays.filter((d) => d !== weekday) : [...block.weekdays, weekday].sort() })}
                      aria-pressed={on}
                      className={clsx("h-8 flex-1 rounded-lg text-xs font-semibold transition", on ? "bg-flame-500/25 text-flame-200" : "bg-white/5 text-mist hover:text-white")}
                    >
                      {t(day)}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((preset) => (
              <button key={preset.label} onClick={() => setBusy((all) => [...all, { ...preset.block, label: t(preset.block.label) }])} className="rounded-xl bg-white/5 px-3 py-1.5 text-sm text-mist hover:bg-white/10 hover:text-white">
                + {t(preset.label)}
              </button>
            ))}
            <button onClick={() => setBusy((all) => [...all, { label: "", weekdays: [0, 1, 2, 3, 4], start: "09:00", end: "12:00" }])} className="rounded-xl bg-white/5 px-3 py-1.5 text-sm text-mist hover:bg-white/10 hover:text-white">
              + {t("Boshqa")}
            </button>
          </div>
        </div>
      </div>

      <div>
        <Label hint={t("soat:daqiqa · rejaga 80% i ishlatiladi")}>{t("Bo'sh vaqtingiz")}</Label>
        <div className="grid grid-cols-7 gap-1 text-center text-xs">
          {WEEKDAYS_SHORT.map((day, weekday) => (
            <div key={day} className="rounded-xl bg-white/[0.03] px-1 py-2">
              <p className="font-semibold">{t(day)}</p>
              <p className="mt-1 text-mist tabular-nums">{hoursAndMinutes(freeMinutes(wake, sleep, busy, weekday))}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
