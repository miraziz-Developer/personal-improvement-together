"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import { Coins, Send, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";

import { useToast } from "@/components/toast";
import { Badge, Button, Card, EmptyState, PageHeader, Segmented, Skeleton, StreakFlame } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useFeatures } from "@/lib/auth";
import { CATEGORY, minutes, STATUS_LABEL } from "@/lib/format";
import type { Category, Challenge, Participation } from "@/lib/types";
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

function GoalCard({ run }: { run: Participation }) {
  const { t } = useI18n();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const meta = CATEGORY[run.category];
  const Icon = meta.icon;
  const open = run.status === "active" || run.status === "scheduled";
  const share = run.total_days ? run.days_completed / run.total_days : 0;

  async function inviteLink(): Promise<string> {
    const { invite_code } = await api<{ invite_code: string }>(`/me/participations/${run.id}/group`, { method: "POST" });
    return `${window.location.origin}/join/${invite_code}`;
  }

  async function copy() {
    setBusy(true);
    try {
      await navigator.clipboard.writeText(await inviteLink());
      toast("success", t("Taklif havolasi nusxalandi 📋"), t("Do'stlaringizga yuboring — ular shu rejaga qo'shiladi."));
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function telegram() {
    setBusy(true);
    try {
      const link = await inviteLink();
      const text = t("Men bilan birga challenge'ni boshla! Har kuni bir-birimizni ko'rib turamiz 🔥");
      window.open(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`, "_blank", "noopener");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className={clsx("flex flex-col gap-4", !open && "opacity-70")}>
      <Link href={`/c/${run.id}`} className="flex items-start gap-4">
        <div className={`grid size-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${meta.gradient}`}>
          <Icon className="size-6" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate font-display text-lg font-semibold">{run.title}</p>
            <StreakFlame streak={run.current_streak} size="sm" />
          </div>
          <p className="mt-0.5 text-sm text-mist">
            {t(STATUS_LABEL[run.status])} · {t("{done}/{total} kun", { done: run.days_completed, total: run.total_days })}
          </p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/5">
            <div className="bg-flame h-full rounded-full" style={{ width: `${share * 100}%` }} />
          </div>
        </div>
      </Link>
      {open && (
        <div className="flex flex-wrap gap-2">
          <Button href={`/c/${run.id}`} size="sm" variant="secondary">
            {t("Ochish")}
          </Button>
          <Button size="sm" variant="ghost" loading={busy} onClick={copy}>
            <Users className="size-4" /> {t("Do'stlarni taklif qilish")}
          </Button>
          <Button size="sm" variant="ghost" onClick={telegram} disabled={busy} aria-label={t("Telegram'da ulashish")}>
            <Send className="size-4" />
          </Button>
        </div>
      )}
    </Card>
  );
}

/** Everything I am on (open first), and what I finished. */
function MyGoals() {
  const { t } = useI18n();
  const { data } = useSWR<Participation[]>("/me/participations");
  if (!data) return <Skeleton className="h-64" />;
  if (data.length === 0) {
    return (
      <Card>
        <EmptyState
          icon="🎯"
          title={t("Hali maqsad yo'q")}
          body={t("Maqsad qo'shing — AI reja tuzadi yoki tayyor challenge tanlaysiz. Har kuni nima qilish «Bugun» sahifasida chiqadi.")}
          action={<Button href="/onboarding">{t("＋ Yangi maqsad")}</Button>}
        />
      </Card>
    );
  }
  const open = data.filter((run) => run.status === "active" || run.status === "scheduled");
  const finished = data.filter((run) => !open.includes(run));
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 lg:grid-cols-2">
        {open.map((run) => (
          <GoalCard key={run.id} run={run} />
        ))}
      </div>
      {finished.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-mist">{t("Tarix")}</h2>
          <div className="grid gap-4 lg:grid-cols-2">
            {finished.map((run) => (
              <GoalCard key={run.id} run={run} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Catalog() {
  const { data } = useSWR<Challenge[]>("/challenges");
  const [filter, setFilter] = useState<Category | "all">("all");
  const { stakesEnabled } = useFeatures();
  const { t } = useI18n();
  const [tab, setTab] = useState<"catalog" | "mine">("mine");
  const shown = data?.filter((c) => filter === "all" || c.category === filter);
  const categories = Array.from(new Set(data?.map((c) => c.category) ?? []));

  return (
    <div>
      <PageHeader
        title={t("Maqsadlarim")}
        subtitle={t("Siz qatnashayotgan challenge'lar va tanlash uchun katalog.")}
        action={<Button href="/onboarding">{t("＋ Yangi maqsad")}</Button>}
      />
      <Segmented<"catalog" | "mine">
        value={tab}
        onChange={setTab}
        options={[
          { value: "mine", label: t("Mening maqsadlarim") },
          { value: "catalog", label: t("Katalog") },
        ]}
      />
      <div className="h-6" />
      {tab === "mine" ? (
        <MyGoals />
      ) : (
        <>
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
        </>
      )}
    </div>
  );
}
