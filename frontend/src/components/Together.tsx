"use client";

import clsx from "clsx";
import { Check, Copy, Crown, Send, Users } from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import useSWR from "swr";

import { ReportButton } from "@/components/ReportButton";
import { useToast } from "@/components/toast";
import { Button, Card, StreakFlame } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import type { GroupBoard, GroupMember } from "@/lib/types";

const noSubscription = () => () => {};
const readOrigin = () => window.location.origin;

const TODAY: Record<string, { icon: string; label: string }> = {
  done: { icon: "✅", label: "bugun bajardi" },
  pending: { icon: "⏳", label: "bugun hali" },
  awaiting_review: { icon: "👀", label: "tekshirilmoqda" },
  frozen: { icon: "🧊", label: "freeze" },
  missed: { icon: "💤", label: "o'tkazib yubordi" },
};

function MemberRow({ member, rank }: { member: GroupMember; rank: number }) {
  const today = member.today_status ? TODAY[member.today_status] : { icon: "🌿", label: "dam olish" };
  const progress = member.total_days ? member.days_completed / member.total_days : 0;
  return (
    <li className={clsx("flex items-center gap-3 rounded-2xl px-3 py-2.5", member.is_me ? "bg-flame-500/10" : "bg-white/[0.02]")}>
      <span className="w-5 text-center font-display text-sm font-bold text-mist">{rank}</span>
      <div className="bg-flame grid size-9 shrink-0 place-items-center rounded-xl font-display text-sm font-bold uppercase">
        {member.username[0]}
      </div>
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 truncate font-medium">
          {member.username}
          {member.is_owner && <Crown className="size-3.5 shrink-0 text-amberish" />}
          {member.is_me ? <span className="text-xs text-mist">(siz)</span> : <ReportButton username={member.username} />}
        </p>
        <div className="mt-1 flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
            <div className="bg-flame h-full rounded-full" style={{ width: `${progress * 100}%` }} />
          </div>
          <span className="text-xs text-mist tabular-nums">
            {member.days_completed}/{member.total_days}
          </span>
        </div>
      </div>
      <span title={today.label} className="text-lg">
        {today.icon}
      </span>
      <StreakFlame streak={member.current_streak} size="sm" />
    </li>
  );
}

/** "Together": invite friends to the same plan and see how everyone is doing today. */
export function TogetherCard({ participationId, open }: { participationId: string; open: boolean }) {
  const toast = useToast();
  const { data: board, mutate } = useSWR<GroupBoard | null>(`/me/participations/${participationId}/group`, {
    refreshInterval: 30_000,
  });
  const origin = useSyncExternalStore(noSubscription, readOrigin, () => "");
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);

  async function createGroup() {
    setCreating(true);
    try {
      await api(`/me/participations/${participationId}/group`, { method: "POST" });
      await mutate();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setCreating(false);
    }
  }

  if (board === undefined) return null;

  if (board === null) {
    if (!open) return null;
    return (
      <Card className="relative overflow-hidden">
        <div className="bg-flame absolute -top-16 -right-16 size-40 rounded-full opacity-15 blur-3xl" />
        <h2 className="relative flex items-center gap-2 font-display text-lg font-semibold">
          <Users className="size-5 text-flame-400" /> Birga kuchliroq
        </h2>
        <p className="relative mt-2 text-sm leading-relaxed text-mist">
          Do'stlaringizni taklif qiling: bir xil reja, umumiy reyting. Kim bugun bajarganini ko'rib turasiz — va orqada qolish
          uyat bo'ladi 😉
        </p>
        <Button className="relative mt-4 w-full" loading={creating} onClick={createGroup}>
          <Users className="size-4" /> Do'stlarni taklif qilish
        </Button>
      </Card>
    );
  }

  const link = `${origin}/join/${board.invite_code}`;
  const shareText = "Men bilan birga challenge'ni boshla! Har kuni bir-birimizni ko'rib turamiz 🔥";
  const telegramShare = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(shareText)}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast("error", "Nusxalab bo'lmadi — havolani qo'lda belgilang.");
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
          <Users className="size-5 text-flame-400" /> Guruh
        </h2>
        <span className="text-sm text-mist">{board.members.length} kishi</span>
      </div>

      <ul className="mt-4 flex flex-col gap-1.5">
        {board.members.map((member, index) => (
          <MemberRow key={member.username} member={member} rank={index + 1} />
        ))}
      </ul>

      {open && (
        <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.02] p-3">
          <p className="text-xs text-mist">Taklif havolasi</p>
          <div className="mt-2 flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-xl bg-ink-900/70 px-3 py-2 text-sm">{link}</code>
            <Button variant="secondary" size="sm" onClick={copy} aria-label="Nusxalash">
              {copied ? <Check className="size-4 text-mint" /> : <Copy className="size-4" />}
            </Button>
          </div>
          <Button href={telegramShare} external variant="sky" size="sm" className="mt-2 w-full">
            <Send className="size-4" /> Telegram'da ulashish
          </Button>
        </div>
      )}
    </Card>
  );
}
