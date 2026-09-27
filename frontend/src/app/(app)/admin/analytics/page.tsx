"use client";

import { AlertTriangle, ArrowLeft } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { Button, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { shortDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

type Analytics = {
  users: number;
  new_7d: number;
  new_30d: number;
  telegram_share: number | null;
  google_share: number | null;
  dau: number;
  wau: number;
  mau: number;
  funnel: { label: string; count: number }[];
  retention_d1: number | null;
  retention_w1: number | null;
  running: number;
  completion_rate: number | null;
  groups: number;
  in_groups: number;
  proofs_30d: number;
  approval_rate: number | null;
  unchecked_30d: number;
  unsafe_30d: number;
  in_review: number;
  daily: { day: string; signups: number; active: number }[];
};

const percent = (share: number | null) => (share === null ? "—" : `${Math.round(share * 100)}%`);

function Tile({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <Card className="p-4">
      <p className="text-sm text-mist">{label}</p>
      <p className="mt-1 font-display text-3xl font-bold tabular-nums">{value}</p>
      {sub && <p className="mt-1 text-xs text-mist">{sub}</p>}
    </Card>
  );
}

/** Active people per day: one series, so the title names it and no legend is needed. */
function ActivityChart({ daily }: { daily: Analytics["daily"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const [asTable, setAsTable] = useState(false);
  const max = Math.max(1, ...daily.map((d) => d.active));
  const point = hover === null ? null : daily[hover];
  const { t } = useI18n();

  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">{t("Faol foydalanuvchilar — oxirgi 30 kun")}</h2>
        <button onClick={() => setAsTable((v) => !v)} className="text-sm text-mist hover:text-white">
          {asTable ? t("Grafik") : t("Jadval")}
        </button>
      </div>
      {asTable ? (
        <div className="mt-4 max-h-72 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-mist">
              <tr>
                <th className="py-1 font-medium">{t("Sana")}</th>
                <th className="py-1 text-right font-medium">{t("Faol")}</th>
                <th className="py-1 text-right font-medium">{t("Yangi")}</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {daily.map((d) => (
                <tr key={d.day} className="border-t border-white/5">
                  <td className="py-1">{shortDate(d.day)}</td>
                  <td className="py-1 text-right">{d.active}</td>
                  <td className="py-1 text-right">{d.signups}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative mt-4">
          <div className="absolute top-0 left-0 text-xs text-mist tabular-nums">{max}</div>
          <div className="flex h-48 items-end gap-[2px] border-b border-white/15 pt-5" onMouseLeave={() => setHover(null)}>
            {daily.map((d, index) => (
              <div
                key={d.day}
                role="img"
                aria-label={`${shortDate(d.day)}: ${t("{active} faol · {new} yangi", { active: d.active, new: d.signups })}`}
                onMouseEnter={() => setHover(index)}
                className="flex h-full flex-1 cursor-default items-end"
              >
                <div
                  className={`w-full rounded-t-[4px] transition-colors ${hover === index ? "bg-flame-300" : "bg-flame-500"}`}
                  style={{ height: `${Math.max((d.active / max) * 100, d.active ? 2 : 0)}%` }}
                />
              </div>
            ))}
          </div>
          <div className="mt-1 flex justify-between text-xs text-mist">
            <span>{shortDate(daily[0].day)}</span>
            <span>{shortDate(daily[daily.length - 1].day)}</span>
          </div>
          {point && (
            <div className="pointer-events-none absolute top-0 right-0 rounded-xl border border-white/10 bg-ink-900/95 px-3 py-2 text-xs shadow-lg">
              <p className="font-semibold">{shortDate(point.day)}</p>
              <p className="text-white/85 tabular-nums">
                {t("{active} faol · {new} yangi", { active: point.active, new: point.signups })}
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

/** Where people drop off. Each bar is relative to the first step; the % is from the step before. */
function Funnel({ steps }: { steps: Analytics["funnel"] }) {
  const { t } = useI18n();
  const top = Math.max(1, steps[0]?.count ?? 1);
  return (
    <Card>
      <h2 className="font-semibold">{t("Voronka")}</h2>
      <ol className="mt-4 flex flex-col gap-3">
        {steps.map((step, index) => {
          const previous = index ? steps[index - 1].count : step.count;
          const kept = previous ? Math.round((step.count / previous) * 100) : 0;
          return (
            <li key={step.label}>
              <div className="flex items-baseline justify-between text-sm">
                <span>{t(step.label)}</span>
                <span className="text-mist tabular-nums">
                  {step.count}
                  {index > 0 && <span className="ml-2 text-xs">({kept}%)</span>}
                </span>
              </div>
              <div className="mt-1 h-2.5 rounded-full bg-white/5">
                <div className="h-full rounded-full bg-flame-500" style={{ width: `${(step.count / top) * 100}%` }} />
              </div>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

export default function AnalyticsPage() {
  const { data, error } = useSWR<Analytics>("/admin/analytics", { refreshInterval: 60_000 });
  const { t, tx } = useI18n();
  if (error) return <EmptyState icon="🔒" title={t("Ruxsat yo'q")} body={errorMessage(error)} />;

  return (
    <div>
      <PageHeader
        title={t("Analitika")}
        subtitle={t("Odamlar keladimi, qaytadimi, oxirigacha yetadimi.")}
        action={
          <Button href="/admin" size="sm" variant="secondary">
            <ArrowLeft className="size-4" /> {t("Moderator paneli")}
          </Button>
        }
      />
      {!data ? (
        <Skeleton className="h-96" />
      ) : (
        <div className="flex flex-col gap-6">
          {data.unchecked_30d > 0 && (
            <Card className="flex items-start gap-3 border-amberish/30 bg-amberish/[0.06]">
              <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amberish" />
              <p className="text-sm">
                {tx("{warning} oxirgi 30 kunda {n} ta isbot AI ishlamagani uchun tekshiruvsiz o'tdi. AI kalitlari va limitlarini tekshiring ({command}).", {
                  warning: <b>{t("Ogohlantirish:")}</b>,
                  n: data.unchecked_30d,
                  command: <code>pit.cli ai-check</code>,
                })}
              </p>
            </Card>
          )}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile label={t("Foydalanuvchilar")} value={data.users} sub={t("+{week} bu hafta · +{month} 30 kunda", { week: data.new_7d, month: data.new_30d })} />
            <Tile label={t("Faol (kun / hafta / oy)")} value={`${data.dau} / ${data.wau} / ${data.mau}`} sub={t("kamida bitta isbot yuborganlar")} />
            <Tile label={t("Qaytish")} value={`${percent(data.retention_d1)} · ${percent(data.retention_w1)}`} sub={t("ertasiga · 2-haftada")} />
            <Tile label={t("Yakunlash")} value={percent(data.completion_rate)} sub={t("{n} ta challenge davom etmoqda", { n: data.running })} />
            <Tile label={t("Guruhlar")} value={data.groups} sub={t("{n} ta qatnashuv guruhda", { n: data.in_groups })} />
            <Tile label="Telegram · Google" value={`${percent(data.telegram_share)} · ${percent(data.google_share)}`} sub={t("ulangan foydalanuvchilar")} />
            <Tile label={t("Isbotlar (30 kun)")} value={data.proofs_30d} sub={t("{share} tasdiqlangan", { share: percent(data.approval_rate) })} />
            <Tile label={t("Moderator navbati")} value={data.in_review} sub={t("{n} ta nomaqbul shubhasi (30 kun)", { n: data.unsafe_30d })} />
          </div>
          <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
            <ActivityChart daily={data.daily} />
            <Funnel steps={data.funnel} />
          </div>
        </div>
      )}
    </div>
  );
}
