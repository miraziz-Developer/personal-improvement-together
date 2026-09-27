"use client";

import clsx from "clsx";
import { BookOpen, ChevronDown, Flag, Map } from "lucide-react";
import { useState } from "react";

import { Card } from "@/components/ui";
import { useI18n } from "@/lib/i18n";
import type { Focus, Roadmap } from "@/lib/types";

/** Today's lesson: the reason today is not a copy of yesterday. */
export function FocusCard({ focus }: { focus: Focus }) {
  const { t } = useI18n();
  return (
    <Card className="relative overflow-hidden border-iris/25 bg-iris/[0.06]">
      <div className="absolute -top-12 -right-12 size-36 rounded-full bg-iris/20 blur-3xl" />
      <div className="relative flex items-start gap-4">
        <div className="grid size-11 shrink-0 place-items-center rounded-2xl bg-iris/20 text-iris">
          <BookOpen className="size-5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold tracking-wide text-iris uppercase">
            {t("{week}-hafta / {weeks}", { week: focus.week, weeks: focus.weeks })} · {focus.theme}
          </p>
          <p className="mt-1 font-display text-lg font-semibold">{focus.lesson ?? t("Bugun — hafta mavzusini mustahkamlash")}</p>
          <p className="mt-1 text-sm text-mist">{t("Hafta maqsadi: {goal}", { goal: focus.goal })}</p>
        </div>
      </div>
    </Card>
  );
}

/** The whole way, week by week; the current week is open. */
export function RoadmapView({ roadmap, current }: { roadmap: Roadmap; current?: number }) {
  const { t } = useI18n();
  const [open, setOpen] = useState<number>(current ?? 1);
  return (
    <Card>
      <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
        <Map className="size-5 text-iris" /> {t("Yo'l xaritasi")}
      </h2>
      <ol className="mt-4 flex flex-col gap-2">
        {roadmap.weeks.map((week, index) => {
          const number = index + 1;
          const expanded = open === number;
          const done = current !== undefined && number < current;
          return (
            <li key={number} className={clsx("rounded-2xl border", number === current ? "border-iris/40 bg-iris/[0.06]" : "border-white/5 bg-white/[0.02]")}>
              <button onClick={() => setOpen(expanded ? 0 : number)} aria-expanded={expanded} className="flex w-full items-start gap-3 p-3 text-left">
                <span
                  className={clsx(
                    "grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold",
                    done ? "bg-mint/20 text-mint" : number === current ? "bg-iris text-white" : "bg-white/10 text-mist",
                  )}
                >
                  {done ? "✓" : number}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold">{week.theme}</span>
                  <span className="block text-sm text-mist">{week.goal}</span>
                </span>
                {week.lessons.length > 0 && <ChevronDown className={clsx("mt-1 size-4 shrink-0 text-mist transition", expanded && "rotate-180")} />}
              </button>
              {expanded && week.lessons.length > 0 && (
                <ol className="flex flex-col gap-1 px-3 pb-3 pl-12 text-sm text-white/85">
                  {week.lessons.map((lesson, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="w-5 shrink-0 text-right text-mist tabular-nums">{i + 1}.</span>
                      {lesson}
                    </li>
                  ))}
                </ol>
              )}
            </li>
          );
        })}
      </ol>
      <p className="mt-4 flex items-start gap-2 rounded-2xl bg-white/[0.03] p-3 text-sm">
        <Flag className="mt-0.5 size-4 shrink-0 text-flame-400" />
        <span>
          <b>{t("Natija:")}</b> {roadmap.outcome}
        </span>
      </p>
    </Card>
  );
}
