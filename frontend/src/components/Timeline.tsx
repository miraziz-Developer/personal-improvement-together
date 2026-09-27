"use client";

import clsx from "clsx";
import { Briefcase, Moon, Sun } from "lucide-react";

import { CATEGORY, minutes } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Category } from "@/lib/types";

export type TimelineEntry = {
  kind: "wake" | "busy" | "task" | "sleep";
  start: string;
  end?: string | null;
  title: string;
  category?: Category | null;
  goal?: string | null; // which goal a task belongs to
  minutes?: number;
  optional?: boolean;
  children?: React.ReactNode; // replaces the task line, e.g. today's task with its proof button
};

/** A day as a vertical line of times: wake up, commitments, every goal's tasks, sleep. */
export function Timeline({ entries, now }: { entries: TimelineEntry[]; now?: string }) {
  const { t } = useI18n();
  const nowIndex = now ? entries.findIndex((e) => e.start > now) : -1;
  return (
    <ol className="relative flex flex-col gap-2 before:absolute before:top-2 before:bottom-2 before:left-[3.25rem] before:w-px before:bg-white/10">
      {entries.map((entry, index) => {
        const meta = entry.category ? CATEGORY[entry.category] : null;
        const Icon = entry.kind === "wake" ? Sun : entry.kind === "sleep" ? Moon : entry.kind === "busy" ? Briefcase : meta?.icon;
        return (
          <li key={`${entry.kind}-${entry.start}-${index}`} className="relative">
            {index === nowIndex && (
              <div className="mb-2 flex items-center gap-2 pl-[2.9rem] text-xs font-semibold text-flame-400">
                <span className="size-2 rounded-full bg-flame-400 shadow-[0_0_10px_rgb(255_120_60/0.8)]" />
                {t("Hozir")} · {now}
              </div>
            )}
            <div className="flex items-start gap-3">
              <span className="w-10 shrink-0 pt-2 text-right text-xs font-semibold text-mist tabular-nums">{entry.start}</span>
              <span
                className={clsx(
                  "relative z-10 mt-1 grid size-7 shrink-0 place-items-center rounded-full",
                  entry.kind === "task" && meta ? `bg-gradient-to-br ${meta.gradient}` : "bg-ink-800 ring-1 ring-white/10",
                )}
              >
                {Icon && <Icon className="size-3.5" />}
              </span>
              <div
                className={clsx(
                  "min-w-0 flex-1 rounded-2xl px-3 py-2",
                  entry.kind === "busy" ? "bg-white/[0.03] text-mist" : entry.kind === "task" && !entry.children ? "bg-white/[0.04]" : "",
                  entry.children && "p-0",
                )}
              >
                {entry.kind === "wake" && <p className="text-sm text-mist">{t("Uyg'onish")}</p>}
                {entry.kind === "sleep" && <p className="text-sm text-mist">{t("Uyqu")}</p>}
                {entry.kind === "busy" && (
                  <p className="text-sm">
                    {entry.title} <span className="text-mist/70">· {t("{from}–{to}", { from: entry.start, to: entry.end ?? "" })}</span>
                  </p>
                )}
                {entry.kind === "task" && entry.children}
                {entry.kind === "task" && !entry.children && (
                  <>
                    <p className="font-semibold">
                      {entry.title}
                      {entry.optional && <span className="ml-2 text-xs font-normal text-mist">{t("qo'shimcha")}</span>}
                    </p>
                    <p className="text-xs text-mist">
                      {[entry.goal, entry.minutes ? minutes(entry.minutes) : null, entry.end ? t("{time} gacha", { time: entry.end }) : null].filter(Boolean).join(" · ")}
                    </p>
                  </>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
