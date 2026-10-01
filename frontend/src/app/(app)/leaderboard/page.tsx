"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import { Crown, Users } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { Button, Card, EmptyState, PageHeader, Segmented, Skeleton } from "@/components/ui";
import type { Leaderboard } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

type Scope = "friends" | "global" | "age" | "region";
type Period = "week" | "season" | "all";

const MEDALS = ["🥇", "🥈", "🥉"];

export default function LeaderboardPage() {
  const { locale, t } = useI18n();
  const [scope, setScope] = useState<Scope>("global");
  const [period, setPeriod] = useState<Period>("week");
  const { data } = useSWR<Leaderboard>(`/leaderboard?scope=${scope}&period=${period}&lang=${locale}`, { refreshInterval: 30_000 });
  const podium = data?.entries.slice(0, 3) ?? [];
  const rest = data?.entries.slice(3) ?? [];

  return (
    <div>
      <PageHeader title={t("Reyting")} subtitle={t("Har bir bajarilgan kun — ball. Uzluksiz streak — ko'proq ball.")} />
      <div className="mb-6 flex flex-wrap gap-3">
        <Segmented<Scope>
          value={scope}
          onChange={setScope}
          options={[
            { value: "friends", label: t("Do'stlar") },
            { value: "global", label: t("Umumiy") },
            { value: "age", label: t("Tengdoshlar") },
            { value: "region", label: t("Hudud") },
          ]}
        />
        <Segmented<Period>
          value={period}
          onChange={setPeriod}
          options={[
            { value: "week", label: t("Hafta") },
            { value: "season", label: t("Oy") },
            { value: "all", label: t("Hammasi") },
          ]}
        />
      </div>

      {!data && <Skeleton className="h-96" />}
      {data && (
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <div className="flex flex-col gap-4">
            <p className="text-sm text-mist">
              {data.title} · {t("{n} ishtirokchi", { n: data.size })}
            </p>
            {scope === "friends" && !data.entries.some((entry) => !entry.is_me) ? (
              <Card>
                <EmptyState
                  icon={<Users className="size-7 text-flame-400" />}
                  title={t("Hali do'stlar bilan challenge yo'q")}
                  body={t("Challenge boshlaganda «👥 Do'stlarim bilan birga»ni tanlang yoki «Maqsadlarim»da «Taklif qilish»ni bosing. Do'stlaringiz qo'shilgach, shu yerda kim oldinda ekanini ko'rasiz.")}
                  action={<Button href="/challenges">{t("Maqsadlarimga o'tish")}</Button>}
                />
              </Card>
            ) : data.hidden ? (
              <Card>
                <EmptyState
                  icon={<Users className="size-7 text-flame-400" />}
                  title={t("Guruh hali kichik")}
                  body={t("Maxfiylik uchun 10 kishidan kam guruhlar ko'rsatilmaydi. Do'stlaringizni taklif qiling — birga qiziqroq!")}
                />
              </Card>
            ) : data.entries.length === 0 ? (
              <Card>
                <EmptyState icon="🏁" title={t("Hali hech kim yo'q")} body={t("Birinchi bo'ling! Bugungi vazifani bajaring — ismingiz shu yerda chiqadi.")} />
              </Card>
            ) : (
              <>
                <div className="grid grid-cols-3 items-end gap-3">
                  {[1, 0, 2].map((i) => {
                    const e = podium[i];
                    if (!e) return <div key={i} />;
                    return (
                      <motion.div
                        key={e.user_id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 * i }}
                        className={clsx(
                          "glass flex flex-col items-center rounded-3xl p-4 text-center",
                          i === 0 && "border-flame-500/40 pb-8",
                          e.is_me && "ring-2 ring-flame-400",
                        )}
                      >
                        {i === 0 && <Crown className="mb-1 size-6 text-amberish" />}
                        <span className="text-3xl">{MEDALS[i]}</span>
                        <p className="mt-2 w-full truncate font-semibold">{e.username}</p>
                        <p className="font-display text-lg font-bold text-flame">{e.points}</p>
                      </motion.div>
                    );
                  })}
                </div>
                <Card className="p-2 sm:p-3">
                  {rest.map((e) => (
                    <div key={e.user_id} className={clsx("flex items-center gap-4 rounded-2xl px-4 py-3", e.is_me && "bg-flame-500/10")}>
                      <span className="w-8 font-display font-bold text-mist">{e.rank}</span>
                      <span className="flex-1 truncate font-medium">
                        {e.username} {e.is_me && <span className="text-flame-400">{t("(siz)")}</span>}
                      </span>
                      <span className="font-semibold tabular-nums">{e.points}</span>
                    </div>
                  ))}
                  {rest.length === 0 && <p className="p-3 text-center text-sm text-mist">{t("Kuchli uchlik! Siz ham shu yerda bo'lishingiz mumkin.")}</p>}
                </Card>
              </>
            )}
          </div>
          <Card className="h-fit text-center">
            <p className="text-sm text-mist">{t("Sizning o'rningiz")}</p>
            <p className="mt-2 font-display text-5xl font-bold text-flame">{data.me ? `#${data.me.rank}` : "—"}</p>
            <p className="mt-2 text-mist">{data.me ? t("{n} ball", { n: data.me.points }) : t("Hali ball yo'q — bugun boshlang!")}</p>
          </Card>
        </div>
      )}
    </div>
  );
}
