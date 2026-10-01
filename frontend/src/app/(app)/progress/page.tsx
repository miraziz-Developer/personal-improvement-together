"use client";

import { ArrowDownRight, ArrowUpRight, Flag, Minus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";

import { Card, EmptyState, PageHeader, Skeleton, StreakFlame } from "@/components/ui";
import { CATEGORY, shortDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Category } from "@/lib/types";

type Progress = {
  days: { day: string; planned: number; done: number }[];
  this_week: number | null;
  last_week: number | null;
  days_done: number;
  best_streak: number;
  runs: {
    participation_id: string;
    title: string;
    category: Category;
    status: string;
    days_completed: number;
    total_days: number;
    current_streak: number;
    month: number | null;
    month_goal: string | null;
  }[];
};

const percent = (share: number | null) => (share === null ? "—" : `${Math.round(share * 100)}%`);

function Tile({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <Card className="p-4">
      <p className="text-sm text-mist">{label}</p>
      <div className="mt-1 font-display text-3xl font-bold tabular-nums">{value}</div>
      {sub && <div className="mt-1 text-xs text-mist">{sub}</div>}
    </Card>
  );
}

/** The week against the one before: an arrow and words, never colour alone. */
function Change({ now, before }: { now: number | null; before: number | null }) {
  const { t } = useI18n();
  if (now === null || before === null) return <span>{t("o'tgan hafta bilan solishtirish uchun ma'lumot kam")}</span>;
  const delta = Math.round((now - before) * 100);
  const Icon = delta > 0 ? ArrowUpRight : delta < 0 ? ArrowDownRight : Minus;
  return (
    <span className="inline-flex items-center gap-1">
      <Icon className="size-3.5" />
      {delta === 0 ? t("o'tgan haftadek") : t("o'tgan haftaga nisbatan {delta}%", { delta: delta > 0 ? `+${delta}` : delta })}
    </span>
  );
}

/** Share of planned challenge-days done, day by day. One series, so the title names it. */
function DailyChart({ days }: { days: Progress["days"] }) {
  const { t } = useI18n();
  const [hover, setHover] = useState<number | null>(null);
  const [asTable, setAsTable] = useState(false);
  const point = hover === null ? null : days[hover];

  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">{t("Oxirgi 30 kun — rejadagi kunlarning bajarilgan ulushi")}</h2>
        <button onClick={() => setAsTable((v) => !v)} className="shrink-0 text-sm text-mist hover:text-white">
          {asTable ? t("Grafik") : t("Jadval")}
        </button>
      </div>
      {asTable ? (
        <div className="mt-4 max-h-72 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-mist">
              <tr>
                <th className="py-1 font-medium">{t("Sana")}</th>
                <th className="py-1 text-right font-medium">{t("Bajarildi")}</th>
                <th className="py-1 text-right font-medium">{t("Rejada")}</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {[...days].reverse().map((d) => (
                <tr key={d.day} className="border-t border-white/5">
                  <td className="py-1">{shortDate(d.day)}</td>
                  <td className="py-1 text-right">{d.done}</td>
                  <td className="py-1 text-right">{d.planned}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative mt-4">
          <div className="absolute top-0 left-0 text-xs text-mist tabular-nums">100%</div>
          {days.every((d) => d.planned === 0) && (
            <p className="absolute inset-0 grid place-items-center px-6 text-center text-sm text-mist">
              {t("Birinchi bajarilgan kundan keyin shu yerda ustunlar o'sib boradi")}
            </p>
          )}
          <div className="flex h-44 items-end gap-[2px] border-b border-white/15 pt-5" onMouseLeave={() => setHover(null)}>
            {days.map((d, index) => {
              const share = d.planned ? d.done / d.planned : 0;
              return (
                <div
                  key={d.day}
                  role="img"
                  aria-label={`${shortDate(d.day)}: ${d.done}/${d.planned}`}
                  onMouseEnter={() => setHover(index)}
                  className="flex h-full flex-1 cursor-default items-end"
                >
                  <div
                    className={`w-full rounded-t-[4px] transition-colors ${hover === index ? "bg-flame-300" : "bg-flame-500"}`}
                    style={{ height: `${Math.max(share * 100, d.done ? 2 : 0)}%` }}
                  />
                </div>
              );
            })}
          </div>
          <div className="mt-1 flex justify-between text-xs text-mist">
            <span>{shortDate(days[0].day)}</span>
            <span>{t("Bugun")}</span>
          </div>
          {point && (
            <div className="pointer-events-none absolute top-0 right-0 rounded-xl border border-white/10 bg-ink-900/95 px-3 py-2 text-xs shadow-lg">
              <p className="font-semibold">{shortDate(point.day)}</p>
              <p className="text-white/85 tabular-nums">
                {point.planned ? t("{done}/{planned} bajarildi", { done: point.done, planned: point.planned }) : t("rejada hech narsa yo'q")}
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default function ProgressPage() {
  const { t } = useI18n();
  const { data } = useSWR<Progress>("/me/progress");

  if (!data) return <Skeleton className="h-96" />;
  const nothingYet = data.days.every((d) => d.planned === 0) && data.runs.length === 0;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={t("Progress")} subtitle={t("Qanchalik oldinga siljiyapsiz — kunma-kun")} />
      {nothingYet ? (
        <Card>
          <EmptyState icon="📈" title={t("Hali ma'lumot yo'q")} body={t("Challenge boshlang — birinchi kundan boshlab grafik o'sib boradi.")} />
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {data.this_week === null ? (
              <Tile label={t("Shu hafta")} value={t("Hali yo'q")} sub={t("Birinchi kun yopilgach hisoblanadi")} />
            ) : (
              <Tile label={t("Shu hafta")} value={percent(data.this_week)} sub={<Change now={data.this_week} before={data.last_week} />} />
            )}
            <Tile label={t("Bajarilgan kunlar")} value={data.days_done} sub={t("barcha challenge'lar bo'yicha")} />
            <Tile label={t("Eng uzun streak")} value={<StreakFlame streak={data.best_streak} />} />
          </div>
          <DailyChart days={data.days} />
          {data.runs.length > 0 && (
            <Card>
              <h2 className="font-semibold">{t("Faol challenge'lar")}</h2>
              <ul className="mt-4 flex flex-col gap-4">
                {data.runs.map((run) => {
                  const meta = CATEGORY[run.category];
                  const Icon = meta.icon;
                  const share = run.total_days ? run.days_completed / run.total_days : 0;
                  return (
                    <li key={run.participation_id}>
                      <Link href={`/c/${run.participation_id}`} className="flex items-center gap-3 rounded-2xl p-1 hover:bg-white/[0.03]">
                        <div className={`grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${meta.gradient}`}>
                          <Icon className="size-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <p className="truncate font-medium">{run.title}</p>
                            <span className="shrink-0 text-sm text-mist tabular-nums">
                              {run.days_completed}/{run.total_days}
                            </span>
                          </div>
                          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/5">
                            <div className="bg-flame h-full rounded-full" style={{ width: `${share * 100}%` }} />
                          </div>
                          {run.month_goal && (
                            <p className="mt-1.5 flex items-center gap-1.5 text-xs text-mist">
                              <Flag className="size-3.5 shrink-0" /> {t("{month}-oy marrasi: {goal}", { month: run.month ?? 1, goal: run.month_goal })}
                            </p>
                          )}
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
