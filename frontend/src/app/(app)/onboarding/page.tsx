"use client";

import clsx from "clsx";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, ArrowRight, Compass, Sparkles, Wand2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { CoachAvatar } from "@/components/coach";
import { useToast } from "@/components/toast";
import { Button, Card, Label, Textarea } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { WEEKDAYS, minutes } from "@/lib/format";
import type { Plan } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const GOAL_IDEAS = ["3 oyda backend dasturchi bo'lish", "Ingliz tilida erkin gapirish", "Har kuni sport bilan shug'ullanish", "Yiliga 24 ta kitob o'qish", "Erta turishni odat qilish"];
const OBSTACLES = ["Vaqt kam", "Charchoq", "Telefon chalg'itadi", "Motivatsiya tez so'nadi", "Boshlash qiyin"];
const PRESETS: { label: string; week: number[] }[] = [
  { label: "Ish kunlari 1 soat", week: [60, 60, 60, 60, 60, 0, 0] },
  { label: "Har kuni 30 daq", week: [30, 30, 30, 30, 30, 30, 30] },
  { label: "Kechqurun 2 soat", week: [120, 120, 120, 120, 120, 180, 60] },
];

const COACH_LINES = [
  "Katta o'zgarish aniq maqsaddan boshlanadi. Nimaga erishmoqchisiz?",
  "Sababingiz — qiyin kunlardagi yoqilg'ingiz. Uni yozib qo'yamiz.",
  "Nima xalaqit berishini bilsak, rejani shunga moslaymiz.",
  "Rejani faqat bo'sh vaqtingizning 80% iga tuzamiz — hayotga ham joy qoladi.",
];

export default function Onboarding() {
  const router = useRouter();
  const toast = useToast();
  const { t } = useI18n();
  const [step, setStep] = useState(-1);
  const [goal, setGoal] = useState("");
  const [motivation, setMotivation] = useState("");
  const [level, setLevel] = useState("");
  const [obstacles, setObstacles] = useState<string[]>([]);
  const [availability, setAvailability] = useState([60, 60, 60, 60, 60, 90, 0]);
  const [loading, setLoading] = useState(false);

  const canNext = step === 0 ? goal.trim().length >= 3 : step === 3 ? availability.some((m) => m >= 20) : true;

  async function generate() {
    setLoading(true);
    try {
      const plan = await api<Plan>("/plans", {
        method: "POST",
        json: { goal, motivation, current_level: level, obstacles: obstacles.map((o) => t(o)).join(", "), availability },
      });
      router.push(`/plans/${plan.id}`);
    } catch (error) {
      toast("error", errorMessage(error));
      setLoading(false);
    }
  }

  if (step === -1) {
    return (
      <div className="mx-auto max-w-3xl">
        <h1 className="font-display text-3xl font-bold">{t("Qaysi yo'ldan boramiz?")}</h1>
        <p className="mt-2 text-mist">{t("Ikkalasi ham to'g'ri. Muhimi — bugun boshlash.")}</p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <button onClick={() => setStep(0)} className="glass group rounded-3xl p-6 text-left transition hover:border-flame-500/40">
            <div className="bg-flame glow-flame grid size-12 place-items-center rounded-2xl">
              <Wand2 className="size-6" />
            </div>
            <h2 className="mt-5 font-display text-xl font-semibold">{t("Menga reja tuz ✨")}</h2>
            <p className="mt-2 text-mist">{t("4 ta savol — va AI maqsadingizga, vaqtingizga mos shaxsiy haftalik reja tuzadi.")}</p>
            <span className="mt-5 inline-flex items-center gap-1 font-semibold text-flame-400 group-hover:gap-2">
              {t("Boshlash")} <ArrowRight className="size-4 transition-all" />
            </span>
          </button>
          <button onClick={() => router.push("/challenges")} className="glass group rounded-3xl p-6 text-left transition hover:border-white/25">
            <div className="grid size-12 place-items-center rounded-2xl bg-white/10">
              <Compass className="size-6" />
            </div>
            <h2 className="mt-5 font-display text-xl font-semibold">{t("Tayyor challenge")}</h2>
            <p className="mt-2 text-mist">{t("Sport, kitob, kod, til, erta turish — sinalgan challenge'lardan birini tanlang.")}</p>
            <span className="mt-5 inline-flex items-center gap-1 font-semibold text-white/80 group-hover:gap-2">
              {t("Katalogni ochish")} <ArrowRight className="size-4 transition-all" />
            </span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex gap-1.5">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
            <motion.div className="bg-flame h-full" initial={false} animate={{ width: i <= step ? "100%" : "0%" }} />
          </div>
        ))}
      </div>

      <div className="mb-6 flex items-start gap-3">
        <CoachAvatar />
        <div className="glass rounded-2xl rounded-tl-sm px-4 py-3 text-white/90">{t(COACH_LINES[step])}</div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} transition={{ duration: 0.25 }}>
          <Card className="flex flex-col gap-5">
            {step === 0 && (
              <>
                <label>
                  <Label>{t("Maqsadingiz")}</Label>
                  <Textarea value={goal} onChange={(e) => setGoal(e.target.value)} placeholder={t("Masalan: 3 oyda backend dasturchi bo'lish")} autoFocus />
                </label>
                <div className="flex flex-wrap gap-2">
                  {GOAL_IDEAS.map((idea) => (
                    <button key={idea} onClick={() => setGoal(t(idea))} className="rounded-xl bg-white/5 px-3 py-1.5 text-sm text-mist transition hover:bg-white/10 hover:text-white">
                      {t(idea)}
                    </button>
                  ))}
                </div>
              </>
            )}
            {step === 1 && (
              <>
                <label>
                  <Label>{t("Bu siz uchun nega muhim?")}</Label>
                  <Textarea
                    value={motivation}
                    onChange={(e) => setMotivation(e.target.value)}
                    placeholder={t("Masalan: yaxshi ishga kirib, oilamga yordam berish")}
                    autoFocus
                  />
                </label>
                <label>
                  <Label>{t("Hozirgi darajangiz")}</Label>
                  <Textarea value={level} onChange={(e) => setLevel(e.target.value)} placeholder={t("Masalan: Python asoslarini bilaman")} className="min-h-20" />
                </label>
              </>
            )}
            {step === 2 && (
              <div>
                <Label>{t("Nima xalaqit beradi? (bir nechtasini tanlang)")}</Label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {OBSTACLES.map((o) => {
                    const on = obstacles.includes(o);
                    return (
                      <button
                        key={o}
                        onClick={() => setObstacles((all) => (on ? all.filter((x) => x !== o) : [...all, o]))}
                        className={clsx("rounded-xl px-3.5 py-2 text-sm font-medium transition", on ? "bg-flame text-white" : "bg-white/5 text-mist hover:text-white")}
                      >
                        {t(o)}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            {step === 3 && (
              <div className="flex flex-col gap-4">
                <div className="flex flex-wrap gap-2">
                  {PRESETS.map((p) => (
                    <button key={p.label} onClick={() => setAvailability(p.week)} className="rounded-xl bg-white/5 px-3 py-1.5 text-sm text-mist hover:bg-white/10 hover:text-white">
                      {t(p.label)}
                    </button>
                  ))}
                </div>
                {WEEKDAYS.map((day, i) => (
                  <label key={day} className="grid grid-cols-[92px_1fr_76px] items-center gap-3">
                    <span className="text-sm font-medium">{t(day)}</span>
                    <input
                      type="range"
                      min={0}
                      max={240}
                      step={15}
                      value={availability[i]}
                      onChange={(e) => setAvailability((a) => a.map((v, j) => (j === i ? Number(e.target.value) : v)))}
                    />
                    <span className={clsx("text-right text-sm tabular-nums", availability[i] ? "text-white" : "text-mist")}>
                      {availability[i] ? minutes(availability[i]) : t("bo'sh emas")}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </Card>
        </motion.div>
      </AnimatePresence>

      <div className="mt-6 flex justify-between gap-3">
        <Button variant="ghost" onClick={() => setStep((s) => s - 1)}>
          <ArrowLeft className="size-4" /> {t("Orqaga")}
        </Button>
        {step < 3 ? (
          <Button disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
            {t("Keyingisi")} <ArrowRight className="size-4" />
          </Button>
        ) : (
          <Button disabled={!canNext} loading={loading} onClick={generate}>
            <Sparkles className="size-4" /> {t("Reja tuzish")}
          </Button>
        )}
      </div>
    </div>
  );
}
