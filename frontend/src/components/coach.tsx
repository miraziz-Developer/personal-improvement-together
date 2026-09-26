"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import { Quote, Sparkles } from "lucide-react";
import Link from "next/link";
import useSWR from "swr";

import { Card, Skeleton } from "@/components/ui";
import { timeAgo } from "@/lib/format";
import type { Notification } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const MOMENT_EMOJI: Record<string, string> = {
  challenge_started: "🚀",
  day_done: "✅",
  streak_milestone: "🏆",
  day_frozen: "🧊",
  challenge_failed: "🌱",
  challenge_completed: "🎉",
  proof_rejected: "📸",
  proof_in_review: "👀",
  morning: "☀️",
  rest_day: "🌿",
  evening_reminder: "⏰",
  friend_day_done: "🔥",
  friend_joined: "👋",
  weekly_great: "🏆",
  weekly_ok: "📊",
  weekly_tough: "🌱",
  cheer: "👏",
};

export function CoachAvatar({ className }: { className?: string }) {
  return (
    <div className={clsx("relative grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-iris to-blush", className)}>
      <Sparkles className="size-5 text-white" />
      <span className="absolute -right-0.5 -bottom-0.5 size-3 rounded-full border-2 border-ink-900 bg-mint" />
    </div>
  );
}

export function QuoteCard() {
  const { locale, t } = useI18n();
  const { data } = useSWR<{ text: string; author: string }>(`/quote?lang=${locale}`);
  return (
    <Card className="relative overflow-hidden">
      <Quote className="absolute -top-2 -right-2 size-24 text-white/[0.04]" />
      <p className="text-xs font-semibold tracking-widest text-flame-400 uppercase">{t("Kun hikmati")}</p>
      {data ? (
        <>
          <p className="mt-3 font-display text-lg leading-snug">«{data.text}»</p>
          <p className="mt-2 text-sm text-mist">— {data.author}</p>
        </>
      ) : (
        <Skeleton className="mt-3 h-14" />
      )}
    </Card>
  );
}

export function NotificationItem({ item, index = 0 }: { item: Notification; index?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={clsx(
        "flex gap-3 rounded-2xl p-3.5 transition",
        item.read ? "bg-white/[0.02]" : "border border-flame-500/20 bg-flame-500/[0.06]",
      )}
    >
      <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/5 text-xl">
        {MOMENT_EMOJI[item.moment] ?? "💬"}
      </div>
      <div className="min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <p className="font-semibold">{item.title}</p>
          <span className="shrink-0 text-xs text-mist">{timeAgo(item.created_at)}</span>
        </div>
        <p className="mt-0.5 text-sm leading-relaxed text-white/75">{item.body}</p>
      </div>
    </motion.div>
  );
}

export function CoachFeed({ limit = 4 }: { limit?: number }) {
  const { t } = useI18n();
  const { data } = useSWR<Notification[]>(`/me/notifications?limit=${limit}`, { refreshInterval: 20_000 });
  return (
    <Card>
      <div className="mb-4 flex items-center gap-3">
        <CoachAvatar />
        <div className="flex-1">
          <p className="font-display font-semibold">{t("Murabbiyingiz")}</p>
          <p className="text-sm text-mist">{t("Har qadamingizda yoningizda")}</p>
        </div>
        <Link href="/notifications" className="text-sm font-semibold text-flame-400 hover:text-flame-300">
          {t("Hammasi")}
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {!data && [0, 1, 2].map((i) => <Skeleton key={i} className="h-16" />)}
        {data?.length === 0 && (
          <p className="rounded-2xl bg-white/[0.03] p-4 text-sm text-mist">
            {t("Birinchi challenge'ingizni boshlang — men har kuni siz bilan bo'laman. 💪")}
          </p>
        )}
        {data?.map((item, i) => <NotificationItem key={item.id} item={item} index={i} />)}
      </div>
    </Card>
  );
}
