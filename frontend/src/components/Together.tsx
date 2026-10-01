"use client";

import clsx from "clsx";
import { Check, Copy, Crown, Send, Users } from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import useSWR from "swr";

import { ReportButton } from "@/components/ReportButton";
import { useToast } from "@/components/toast";
import { Button, Card, StreakFlame } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { GroupBoard, GroupMember } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const noSubscription = () => () => {};
const readOrigin = () => window.location.origin;

const TODAY: Record<string, { icon: string; label: string }> = {
  done: { icon: "✅", label: "bugun bajardi" },
  pending: { icon: "⏳", label: "bugun hali" },
  awaiting_review: { icon: "👀", label: "tekshirilmoqda" },
  frozen: { icon: "🧊", label: "freeze" },
  missed: { icon: "💤", label: "o'tkazib yubordi" },
};

function CheerButton({ participationId, username }: { participationId: string; username: string }) {
  const toast = useToast();
  const { t } = useI18n();
  const [sent, setSent] = useState(false);

  async function cheer() {
    try {
      await api(`/me/participations/${participationId}/group/cheer`, { method: "POST", json: { username, emoji: "👏" } });
      setSent(true);
      toast("success", t("👏 {name} olqishingizni oldi!", { name: username }));
    } catch (error) {
      toast("error", errorMessage(error));
    }
  }

  return (
    <button
      onClick={cheer}
      disabled={sent}
      aria-label={t("{name}ni olqishlash", { name: username })}
      className="rounded-xl bg-white/5 px-2 py-1 text-sm transition hover:bg-flame-500/20 disabled:opacity-40"
    >
      👏
    </button>
  );
}

function MemberRow({ member, participationId, open }: { member: GroupMember; participationId: string; open: boolean }) {
  const { t } = useI18n();
  const today = member.today_status ? TODAY[member.today_status] : { icon: "🌿", label: "dam olish" };
  const progress = member.total_days ? member.days_completed / member.total_days : 0;
  return (
    <li className={clsx("flex items-center gap-3 rounded-2xl px-3 py-2.5", member.is_me ? "bg-flame-500/10" : "bg-white/[0.02]")}>
      <span className="w-6 shrink-0 text-center font-display text-sm font-bold text-mist">{member.rank}</span>
      <div className="bg-flame grid size-9 shrink-0 place-items-center rounded-xl font-display text-sm font-bold uppercase">
        {member.username[0]}
      </div>
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 truncate font-medium">
          {member.username}
          {member.is_owner && <Crown className="size-3.5 shrink-0 text-amberish" />}
          {member.is_me ? <span className="text-xs text-mist">{t("(siz)")}</span> : <ReportButton username={member.username} />}
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
      <span title={t(today.label)} className="text-lg">
        {today.icon}
      </span>
      {open && !member.is_me && <CheerButton participationId={participationId} username={member.username} />}
      <StreakFlame streak={member.current_streak} size="sm" />
    </li>
  );
}

/** "Together": invite friends to the same plan and see how everyone is doing today. */
type Message = { id: string; username: string; text: string; created_at: string; is_me: boolean };
const MAX_MESSAGE = 280;
const GROUP_TOP = 10; // rows shown before "see everyone"

/** Short words between friends: "done for today", "don't give up". Members only. */
function GroupChat({ participationId, open }: { participationId: string; open: boolean }) {
  const { t } = useI18n();
  const toast = useToast();
  const key = `/me/participations/${participationId}/group/messages`;
  const { data: messages, mutate } = useSWR<Message[]>(key, { refreshInterval: 20_000 });
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    setSending(true);
    try {
      await api(key, { method: "POST", json: { text: text.trim() } });
      setText("");
      await mutate();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mt-5">
      <p className="text-xs font-semibold text-mist">{t("Guruh xabarlari")}</p>
      <ul className="mt-2 flex max-h-64 flex-col gap-1.5 overflow-y-auto">
        {messages?.length === 0 && <li className="text-sm text-mist">{t("Hali xabar yo'q — birinchi bo'lib do'stlaringizni ruhlantiring 💬")}</li>}
        {messages?.map((message) => (
          <li key={message.id} className={clsx("rounded-2xl px-3 py-2 text-sm", message.is_me ? "ml-8 bg-flame-500/10" : "mr-8 bg-white/[0.04]")}>
            <p className="flex items-center gap-1.5 text-xs text-mist">
              <b className="text-white/85">{message.is_me ? t("Siz") : message.username}</b> · {timeAgo(message.created_at)}
              {!message.is_me && <ReportButton username={message.username} />}
            </p>
            <p className="mt-0.5 break-words whitespace-pre-line">{message.text}</p>
          </li>
        ))}
      </ul>
      {open && (
        <form onSubmit={send} className="mt-2 flex items-center gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={MAX_MESSAGE}
            placeholder={t("Do'stlaringizga yozing…")}
            aria-label={t("Guruhga xabar")}
            className="h-10 min-w-0 flex-1 rounded-2xl border border-white/10 bg-ink-900/70 px-3 text-sm outline-none focus:border-flame-500/70"
          />
          <Button type="submit" size="sm" loading={sending} disabled={!text.trim()} aria-label={t("Yuborish")}>
            <Send className="size-4" />
          </Button>
        </form>
      )}
    </div>
  );
}

export function TogetherCard({ participationId, open }: { participationId: string; open: boolean }) {
  const toast = useToast();
  const { t } = useI18n();
  const { data: board, mutate } = useSWR<GroupBoard | null>(`/me/participations/${participationId}/group`, {
    refreshInterval: 30_000,
  });
  const origin = useSyncExternalStore(noSubscription, readOrigin, () => "");
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [everyone, setEveryone] = useState(false);

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
          <Users className="size-5 text-flame-400" /> {t("Birga kuchliroq")}
        </h2>
        <p className="relative mt-2 text-sm leading-relaxed text-mist">
          {t(
            "Do'stlaringizni taklif qiling: bir xil reja, umumiy reyting. Kim bugun bajarganini ko'rib turasiz — va orqada qolish uyat bo'ladi 😉",
          )}
        </p>
        <Button className="relative mt-4 w-full" loading={creating} onClick={createGroup}>
          <Users className="size-4" /> {t("Do'stlarni taklif qilish")}
        </Button>
      </Card>
    );
  }

  const link = `${origin}/join/${board.invite_code}`;
  const shareText = t("Men bilan birga challenge'ni boshla! Har kuni bir-birimizni ko'rib turamiz 🔥");
  const telegramShare = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(shareText)}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast("error", t("Nusxalab bo'lmadi — havolani qo'lda belgilang."));
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
          <Users className="size-5 text-flame-400" /> {t("Guruh")}
        </h2>
        <span className="text-sm text-mist">{t("{n} kishi", { n: board.size })}</span>
      </div>

      <ul className="mt-4 flex flex-col gap-1.5">
        {/* Any size of group: the top ten and me, the rest on request. */}
        {board.members
          .filter((member) => everyone || member.rank <= GROUP_TOP || member.is_me)
          .map((member) => (
            <MemberRow key={member.username} member={member} participationId={participationId} open={open} />
          ))}
      </ul>
      {!everyone && board.members.length > GROUP_TOP + 1 && (
        <Button variant="ghost" size="sm" className="mt-2 w-full" onClick={() => setEveryone(true)}>
          {t("Hammasini ko'rish ({n})", { n: board.size })}
        </Button>
      )}
      {board.size > board.members.length && everyone && (
        <p className="mt-2 text-center text-xs text-mist">{t("Eng yaxshi {n} tasi ko'rsatilgan", { n: board.members.length })}</p>
      )}

      {board.size > 1 && <GroupChat participationId={participationId} open={open} />}

      {open && (
        <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.02] p-3">
          {board.size === 1 && (
            <p className="mb-3 text-sm">{t("Hozircha guruhda faqat sizsiz. Havolani do'stlaringizga yuboring — ular qo'shilgach, shu yerda kim oldinda ekani ko'rinadi 🏁")}</p>
          )}
          <p className="text-xs text-mist">{t("Taklif havolasi")}</p>
          <div className="mt-2 flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-xl bg-ink-900/70 px-3 py-2 text-sm">{link}</code>
            <Button variant="secondary" size="sm" onClick={copy} aria-label={t("Nusxalash")}>
              {copied ? <Check className="size-4 text-mint" /> : <Copy className="size-4" />}
            </Button>
          </div>
          <Button href={telegramShare} external variant="sky" size="sm" className="mt-2 w-full">
            <Send className="size-4" /> {t("Telegram'da ulashish")}
          </Button>
        </div>
      )}
    </Card>
  );
}
