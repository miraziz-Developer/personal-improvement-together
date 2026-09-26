"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import { Crown, Users } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { Card, EmptyState, PageHeader, Segmented, Skeleton } from "@/components/ui";
import type { Leaderboard } from "@/lib/types";

type Scope = "global" | "age" | "region";
type Period = "week" | "season" | "all";

const MEDALS = ["🥇", "🥈", "🥉"];

export default function LeaderboardPage() {
  const [scope, setScope] = useState<Scope>("global");
  const [period, setPeriod] = useState<Period>("week");
  const { data } = useSWR<Leaderboard>(`/leaderboard?scope=${scope}&period=${period}`, { refreshInterval: 30_000 });
  const podium = data?.entries.slice(0, 3) ?? [];
  const rest = data?.entries.slice(3) ?? [];

  return (
    <div>
      <PageHeader title="Reyting" subtitle="Har bir bajarilgan kun — ball. Uzluksiz streak — ko'proq ball." />
      <div className="mb-6 flex flex-wrap gap-3">
        <Segmented<Scope>
          value={scope}
          onChange={setScope}
          options={[
            { value: "global", label: "Umumiy" },
            { value: "age", label: "Tengdoshlar" },
            { value: "region", label: "Hudud" },
          ]}
        />
        <Segmented<Period>
          value={period}
          onChange={setPeriod}
          options={[
            { value: "week", label: "Hafta" },
            { value: "season", label: "Oy" },
            { value: "all", label: "Hammasi" },
          ]}
        />
      </div>

      {!data && <Skeleton className="h-96" />}
      {data && (
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <div className="flex flex-col gap-4">
            <p className="text-sm text-mist">
              {data.title} · {data.size} ishtirokchi
            </p>
            {data.hidden ? (
              <Card>
                <EmptyState
                  icon={<Users className="size-7 text-flame-400" />}
                  title="Guruh hali kichik"
                  body="Maxfiylik uchun 10 kishidan kam guruhlar ko'rsatilmaydi. Do'stlaringizni taklif qiling — birga qiziqroq!"
                />
              </Card>
            ) : data.entries.length === 0 ? (
              <Card>
                <EmptyState icon="🏁" title="Hali hech kim yo'q" body="Birinchi bo'ling! Bugungi vazifani bajaring — ismingiz shu yerda chiqadi." />
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
                        {e.username} {e.is_me && <span className="text-flame-400">(siz)</span>}
                      </span>
                      <span className="font-semibold tabular-nums">{e.points}</span>
                    </div>
                  ))}
                  {rest.length === 0 && <p className="p-3 text-center text-sm text-mist">Kuchli uchlik! Siz ham shu yerda bo'lishingiz mumkin.</p>}
                </Card>
              </>
            )}
          </div>
          <Card className="h-fit text-center">
            <p className="text-sm text-mist">Sizning o'rningiz</p>
            <p className="mt-2 font-display text-5xl font-bold text-flame">{data.me ? `#${data.me.rank}` : "—"}</p>
            <p className="mt-2 text-mist">{data.me ? `${data.me.points} ball` : "Hali ball yo'q — bugun boshlang!"}</p>
          </Card>
        </div>
      )}
    </div>
  );
}
