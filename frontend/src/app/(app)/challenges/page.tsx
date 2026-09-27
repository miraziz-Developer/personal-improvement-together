"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import { Coins, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";

import { Badge, Button, PageHeader, Skeleton } from "@/components/ui";
import { useFeatures } from "@/lib/auth";
import { CATEGORY, minutes } from "@/lib/format";
import type { Category, Challenge } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

export function Difficulty({ level }: { level: number }) {
  const { t } = useI18n();
  return (
    <span className="flex gap-0.5" title={t("Qiyinlik {level}/5", { level })}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={clsx("h-3 w-1.5 rounded-full", i <= level ? "bg-flame-400" : "bg-white/10")} />
      ))}
    </span>
  );
}

export default function Catalog() {
  const { data } = useSWR<Challenge[]>("/challenges");
  const [filter, setFilter] = useState<Category | "all">("all");
  const { stakesEnabled } = useFeatures();
  const { t } = useI18n();
  const shown = data?.filter((c) => filter === "all" || c.category === filter);
  const categories = Array.from(new Set(data?.map((c) => c.category) ?? []));

  return (
    <div>
      <PageHeader
        title={t("Challenge'lar")}
        subtitle={t("Sinalgan dasturlar. Har biri — yangi odat sari aniq yo'l.")}
        action={<Button href="/onboarding">{t("✨ O'zimga moslab tuzish")}</Button>}
      />
      <div className="mb-6 flex flex-wrap gap-2">
        {(["all", ...categories] as const).map((c) => (
          <button
            key={c}
            onClick={() => setFilter(c)}
            className={clsx("rounded-xl px-3.5 py-2 text-sm font-semibold transition", filter === c ? "bg-white/10 text-white" : "text-mist hover:text-white")}
          >
            {c === "all" ? t("Hammasi") : t(CATEGORY[c].label)}
          </button>
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {!data && [0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-64" />)}
        {shown?.map((c, i) => {
          const meta = CATEGORY[c.category];
          const Icon = meta.icon;
          return (
            <motion.div key={c.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
              <Link href={`/challenges/${c.id}`} className="glass group flex h-full flex-col overflow-hidden rounded-3xl transition hover:-translate-y-1 hover:border-white/20">
                <div className={`relative h-24 bg-gradient-to-br ${meta.gradient}`}>
                  <Icon className="absolute right-4 bottom-3 size-14 text-white/25 transition group-hover:scale-110" />
                  <span className="absolute top-4 left-4 rounded-full bg-black/25 px-2.5 py-1 text-xs font-semibold backdrop-blur">{t(meta.label)}</span>
                </div>
                <div className="flex flex-1 flex-col p-5">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-display text-lg font-semibold">{c.title}</h3>
                    <Difficulty level={c.difficulty} />
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-mist">{c.description}</p>
                  <div className="mt-auto flex flex-wrap gap-1.5 pt-4">
                    <Badge>{t("{n} kun", { n: c.duration_days })}</Badge>
                    <Badge>{t("{n} kun/hafta", { n: c.days_per_week })}</Badge>
                    <Badge>{t("{time}/hafta", { time: minutes(c.minutes_per_week) })}</Badge>
                    {stakesEnabled && c.stake_allowed && (
                      <Badge className="text-amberish">
                        <Coins className="size-3" /> {t("garov")}
                      </Badge>
                    )}
                    <Badge>
                      <Users className="size-3" /> {c.participants}
                    </Badge>
                  </div>
                </div>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
