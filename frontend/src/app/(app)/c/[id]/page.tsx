"use client";

import confetti from "canvas-confetti";
import { Coins, KeyRound, Snowflake } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import useSWR from "swr";

import { Calendar } from "@/components/Calendar";
import { CoachAvatar } from "@/components/coach";
import { ProofTask } from "@/components/ProofTask";
import { FocusCard, RoadmapView } from "@/components/Roadmap";
import { TogetherCard } from "@/components/Together";
import { useToast } from "@/components/toast";
import { Badge, Button, Card, Modal, ProgressRing, Skeleton, StreakFlame } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CATEGORY, money, shortDate, STATUS_LABEL } from "@/lib/format";
import type { ParticipationDetail } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const CHEERS = [
  "Bugungi kun yopildi! Siz o'zingizga bergan va'dada turdingiz. 🔥",
  "Zo'r! Har bir bajarilgan kun — kelajakdagi o'zingizga sovg'a. 🎁",
  "Barakalla! Tomchi-tomchi ko'l bo'lur. 💧",
];

function celebrate() {
  const colors = ["#ff9a3d", "#ff5f3a", "#ff3d7f", "#34e8a8", "#7c5cff"];
  confetti({ particleCount: 120, spread: 100, origin: { y: 0.6 }, colors });
  setTimeout(() => confetti({ particleCount: 80, angle: 60, spread: 70, origin: { x: 0 }, colors }), 250);
  setTimeout(() => confetti({ particleCount: 80, angle: 120, spread: 70, origin: { x: 1 }, colors }), 400);
}

export default function ParticipationPage() {
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const { t } = useI18n();
  const { refreshMe } = useAuth();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const { data: p, mutate } = useSWR<ParticipationDetail>(`/me/participations/${id}`, {
    refreshInterval: (latest) =>
      latest?.today.tasks.some((task) => task.proof_status === "pending") ? 2000 : 30_000,
  });
  const previous = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    if (!p) return;
    const now = p.today.status;
    if (previous.current !== undefined && previous.current !== "done" && now === "done") {
      celebrate();
      toast("success", t(CHEERS[p.current_streak % CHEERS.length]), t("Streak: {n} kun", { n: p.current_streak }));
      refreshMe();
    }
    if (previous.current !== undefined && p.status === "completed") celebrate();
    previous.current = now;
  }, [p, toast, refreshMe, t]);

  if (!p) return <Skeleton className="h-[480px]" />;
  const meta = CATEGORY[p.category];
  const Icon = meta.icon;
  const requiredLeft = p.today.tasks.filter((task) => task.required && task.proof_status !== "approved").length;

  async function cancel() {
    setCancelling(true);
    try {
      await api(`/me/participations/${id}/cancel`, { method: "POST" });
      toast("info", t("Challenge bekor qilindi"), p?.mode === "stake" ? t("Garov hamyoningizga qaytarildi.") : undefined);
      setCancelOpen(false);
      mutate();
      refreshMe();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card className="relative overflow-hidden">
        <div className={`absolute -top-24 -left-24 size-72 rounded-full bg-gradient-to-br ${meta.gradient} opacity-20 blur-3xl`} />
        <div className="relative flex flex-col items-center gap-6 sm:flex-row">
          <ProgressRing value={p.total_days ? p.days_completed / p.total_days : 0} size={132}>
            <div>
              <p className="font-display text-2xl font-bold">
                {p.days_completed}
                <span className="text-base text-mist">/{p.total_days}</span>
              </p>
              <p className="text-xs text-mist">{t("kun")}</p>
            </div>
          </ProgressRing>
          <div className="flex-1 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <Badge>
                <Icon className="size-3.5" /> {t(meta.label)}
              </Badge>
              <Badge>{t(STATUS_LABEL[p.status])}</Badge>
              <Badge>
                {shortDate(p.start_date)} — {shortDate(p.end_date)}
              </Badge>
            </div>
            <h1 className="mt-3 font-display text-2xl font-bold sm:text-3xl">{p.title}</h1>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-5 sm:justify-start">
              <div>
                <p className="text-xs text-mist">{t("Streak")}</p>
                <StreakFlame streak={p.current_streak} size="md" />
              </div>
              <div>
                <p className="text-xs text-mist">{t("Freeze")}</p>
                <p className="flex items-center gap-1 pt-1">
                  {Array.from({ length: Math.max(p.freezes_left, 0) }).map((_, i) => (
                    <Snowflake key={i} className="size-5 text-ice" />
                  ))}
                  {p.freezes_left === 0 && <span className="text-sm text-mist">{t("qolmadi")}</span>}
                </p>
              </div>
              {p.mode === "stake" && (
                <div>
                  <p className="text-xs text-mist">{t("Garov")}</p>
                  <p className="flex items-center gap-1.5 pt-1 font-semibold text-amberish">
                    <Coins className="size-4" /> {money(p.stake)}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <CoachAvatar className="size-10" />
            <p className="glass flex-1 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-white/90">
              {p.status !== "active"
                ? p.status === "completed"
                  ? t("Siz buni uddaladingiz! Bu g'alaba — faqat sizniki. 🏆")
                  : p.status === "scheduled"
                    ? t("Challenge {date} kuni boshlanadi. Tayyorlaning! 💪", { date: shortDate(p.start_date) })
                    : t("Bu safar chiqmadi — lekin bu oxiri emas. Tayyor bo'lsangiz, qaytadan boshlaymiz. 🌱")
                : p.today.is_rest_day
                  ? t("Bugun dam olish kuni. Tiklanish ham mashqning bir qismi. 🌿")
                  : requiredLeft === 0
                    ? t("Bugungi majburiy vazifalar bajarildi! Qo'shimchalar — bonus ball. ⭐")
                    : t("Bugun {n} ta majburiy vazifa qoldi. Boshladik! 🔥", { n: requiredLeft })}
            </p>
          </div>

          {p.status === "active" && !p.today.is_rest_day && p.today.focus && <FocusCard focus={p.today.focus} />}

          {p.today.daily_code && (
            <Card className="flex items-center gap-4 border-amberish/25 bg-amberish/[0.05]">
              <KeyRound className="size-8 shrink-0 text-amberish" />
              <div className="flex-1">
                <p className="text-sm text-mist">{t("Bugungi kod — qog'ozga yozib, rasmda ko'rsating")}</p>
                <p className="font-mono text-3xl font-bold tracking-[0.3em] text-amberish">{p.today.daily_code}</p>
              </div>
            </Card>
          )}

          {p.status === "active" && !p.today.is_rest_day && (
            <div className="flex flex-col gap-3">
              {p.today.tasks.map((task) => (
                <ProofTask key={task.key} participationId={p.id} task={task} onSubmitted={() => mutate()} />
              ))}
            </div>
          )}

          {p.can_cancel && (
            <Button variant="ghost" className="self-start" onClick={() => setCancelOpen(true)}>
              {t("Boshlanmasdan bekor qilish")}
            </Button>
          )}
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <h2 className="mb-4 font-display text-lg font-semibold">{t("Kalendar")}</h2>
            <Calendar start={p.start_date} end={p.end_date} days={p.calendar} today={p.today.date} />
          </Card>
          <TogetherCard participationId={p.id} open={p.status === "active" || p.status === "scheduled"} />
          {p.roadmap && <RoadmapView roadmap={p.roadmap} current={p.today.focus?.week} />}
        </div>
      </div>

      <Modal open={cancelOpen} onClose={() => setCancelOpen(false)} title={t("Bekor qilasizmi?")}>
        <p className="text-mist">
          {p.mode === "stake"
            ? t("Challenge hali boshlanmagan, shuning uchun garov to'liq qaytariladi.")
            : t("Challenge hali boshlanmagan, shuning uchun hech narsa yo'qotmaysiz.")}
        </p>
        <div className="mt-6 flex gap-2">
          <Button variant="secondary" className="flex-1" onClick={() => setCancelOpen(false)}>
            {t("Qolaman")}
          </Button>
          <Button variant="danger" className="flex-1" loading={cancelling} onClick={cancel}>
            {t("Bekor qilish")}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
