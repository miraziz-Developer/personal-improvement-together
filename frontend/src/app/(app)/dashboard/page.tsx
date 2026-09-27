"use client";

import { motion } from "motion/react";
import { ArrowRight, CalendarClock, CheckCircle2, Sparkles, Star, Target, Trophy } from "lucide-react";
import Link from "next/link";
import useSWR from "swr";

import { CoachFeed, QuoteCard } from "@/components/coach";
import { TelegramNudge } from "@/components/Telegram";
import { Badge, Button, Card, EmptyState, Skeleton, StreakFlame } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { CATEGORY, DAY_STATUS, greeting, STATUS_LABEL } from "@/lib/format";
import type { Participation, Routine } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-center gap-2 text-sm text-mist">
        {icon}
        {label}
      </div>
      <div className="mt-2 font-display text-2xl font-bold">{value}</div>
    </Card>
  );
}

function ParticipationCard({ p, index }: { p: Participation; index: number }) {
  const { t } = useI18n();
  const meta = CATEGORY[p.category];
  const Icon = meta.icon;
  const progress = p.total_days ? p.days_completed / p.total_days : 0;
  const todayDone = p.today_status === "done";
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.06 }}>
      <Link href={`/c/${p.id}`} className="glass group block rounded-3xl p-5 transition hover:border-white/20">
        <div className="flex items-start gap-4">
          <div className={`grid size-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${meta.gradient}`}>
            <Icon className="size-6" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate font-semibold">{p.title}</p>
              <StreakFlame streak={p.current_streak} size="sm" />
            </div>
            <p className="mt-0.5 text-sm text-mist">
              {t(STATUS_LABEL[p.status])} · {t("{done}/{total} kun", { done: p.days_completed, total: p.total_days })}
              {p.mode === "stake" && ` · ${t("💰 garov")}`}
            </p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/5">
              <motion.div className="bg-flame h-full rounded-full" initial={{ width: 0 }} animate={{ width: `${progress * 100}%` }} transition={{ duration: 1 }} />
            </div>
          </div>
        </div>
        {p.status === "active" && (
          <div className="mt-4 flex items-center justify-between rounded-2xl bg-white/[0.03] px-4 py-3">
            {p.today_status ? (
              <span className="flex items-center gap-2 text-sm">
                <span className={`size-2.5 rounded-full ${DAY_STATUS[p.today_status].dot}`} />
                {todayDone ? t("Bugun: bajarildi — barakalla! 🎉") : t("Bugun: {status}", { status: t(DAY_STATUS[p.today_status].label).toLowerCase() })}
              </span>
            ) : (
              <span className="text-sm text-mist">{t("Bugun dam olish kuni 🌿")}</span>
            )}
            {!todayDone && p.today_status && (
              <span className="flex items-center gap-1 text-sm font-semibold text-flame-400 group-hover:gap-2">
                {t("Boshlash")} <ArrowRight className="size-4 transition-all" />
              </span>
            )}
          </div>
        )}
      </Link>
    </motion.div>
  );
}

/** The next few timed tasks of today, across all goals. */
function NextUp() {
  const { t } = useI18n();
  const { data } = useSWR<Routine>("/me/routine", { refreshInterval: 60_000 });
  const now = new Date().toTimeString().slice(0, 5);
  const upcoming = data?.items.filter((i) => i.kind === "task" && (i.end ?? i.start) >= now && i.task?.proof_status !== "approved").slice(0, 3) ?? [];
  if (!data || upcoming.length === 0) return null;
  return (
    <Link href="/routine" className="glass group block rounded-3xl p-5 transition hover:border-iris/40">
      <p className="flex items-center gap-2 font-semibold">
        <CalendarClock className="size-4 text-iris" /> {t("Keyingi vazifalar")}
      </p>
      <ul className="mt-3 flex flex-col gap-2">
        {upcoming.map((item) => (
          <li key={`${item.participation_id}-${item.task?.key}`} className="flex items-center gap-3 text-sm">
            <span className="w-11 shrink-0 font-semibold text-iris tabular-nums">{item.start}</span>
            <span className="min-w-0 flex-1 truncate">{item.title}</span>
          </li>
        ))}
      </ul>
      <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-iris group-hover:gap-2">
        {t("Kun tartibi")} <ArrowRight className="size-4 transition-all" />
      </span>
    </Link>
  );
}

export default function Dashboard() {
  const { me } = useAuth();
  const { t } = useI18n();
  const { data: list } = useSWR<Participation[]>("/me/participations", { refreshInterval: 30_000 });
  const active = list?.filter((p) => p.status === "active" || p.status === "scheduled") ?? [];
  const finished = list?.filter((p) => p.status !== "active" && p.status !== "scheduled") ?? [];
  const pendingToday = active.filter((p) => p.today_status === "pending").length;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-bold sm:text-3xl">{me ? greeting(me.username) : <Skeleton className="h-9 w-64" />}</h1>
        <p className="mt-2 text-mist">
          {pendingToday > 0
            ? t("Bugun {n} ta challenge sizni kutyapti. Kichik qadam — katta natija.", { n: pendingToday })
            : active.length
              ? t("Bugungi rejalar bajarildi. Siz bilan faxrlanamiz! 🔥")
              : t("Keling, birinchi maqsadingizni belgilaymiz.")}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={<Star className="size-4 text-amberish" />} label={t("Ballar")} value={me?.points ?? "—"} />
        <Stat icon={<Sparkles className="size-4 text-flame-400" />} label={t("Eng uzun streak")} value={<StreakFlame streak={me?.best_streak ?? 0} />} />
        <Stat icon={<Target className="size-4 text-ice" />} label={t("Faol")} value={me?.active_challenges ?? "—"} />
        <Stat icon={<Trophy className="size-4 text-mint" />} label={t("Yakunlangan")} value={me?.completed_challenges ?? "—"} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">{t("Challenge'larim")}</h2>
            <Button href="/onboarding" size="sm" variant="secondary">
              {t("+ Yangi")}
            </Button>
          </div>
          {!list && [0, 1].map((i) => <Skeleton key={i} className="h-36" />)}
          {list && active.length === 0 && (
            <Card>
              <EmptyState
                icon="🎯"
                title={t("Hali challenge yo'q")}
                body={t("Maqsadingizni ayting — AI 30 soniyada shaxsiy reja tuzadi. Yoki tayyor challenge'lardan birini tanlang.")}
                action={
                  <div className="flex flex-wrap justify-center gap-2">
                    <Button href="/onboarding">{t("Menga reja tuz ✨")}</Button>
                    <Button href="/challenges" variant="secondary">
                      {t("Katalog")}
                    </Button>
                  </div>
                }
              />
            </Card>
          )}
          {active.map((p, i) => (
            <ParticipationCard key={p.id} p={p} index={i} />
          ))}
          {finished.length > 0 && (
            <div className="mt-2">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-mist">
                <CheckCircle2 className="size-4" /> {t("Tarix")}
              </h3>
              <div className="flex flex-col gap-2">
                {finished.map((p) => (
                  <Link key={p.id} href={`/c/${p.id}`} className="flex items-center justify-between rounded-2xl bg-white/[0.03] px-4 py-3 text-sm hover:bg-white/[0.06]">
                    <span className="truncate">{p.title}</span>
                    <Badge>{t(STATUS_LABEL[p.status])}</Badge>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="flex flex-col gap-6">
          <NextUp />
          <TelegramNudge />
          <QuoteCard />
          <CoachFeed limit={4} />
        </div>
      </div>
    </div>
  );
}
