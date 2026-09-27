"use client";

import clsx from "clsx";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, ArrowRight, Plus, Sparkles, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { CoachAvatar } from "@/components/coach";
import { useToast } from "@/components/toast";
import { Button, Card, Input, Label, Textarea } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { CATEGORY, WEEKDAYS_SHORT } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { freeMinutes } from "@/lib/routine";
import type { BusyBlock, LifePlan, RoutineCandidate } from "@/lib/types";

const MAX_GOALS = 3;
const GOAL_IDEAS = ["Kuchli backend dasturchi bo'lish", "Muskulli tana, 5 kg massa", "Ingliz tilida erkin gapirish", "Yiliga 24 ta kitob o'qish"];
const PRESETS: { label: string; block: BusyBlock }[] = [
  { label: "Ish: Du–Ju 09:00–18:00", block: { label: "Ish", weekdays: [0, 1, 2, 3, 4], start: "09:00", end: "18:00" } },
  { label: "O'qish: Du–Sha 08:00–13:00", block: { label: "O'qish", weekdays: [0, 1, 2, 3, 4, 5], start: "08:00", end: "13:00" } },
];
const DURATIONS = [
  { days: 30, title: "30 kun", body: "Bir oylik sinov: odatlar shakllanadi." },
  { days: 60, title: "60 kun", body: "Ikki oy va 2 ta oylik marra." },
  { days: 90, title: "90 kun", body: "Uch oy va 3 ta oylik marra — katta o'zgarish." },
];
type Step = "goals" | "runs" | "day" | "duration";
const COACH_LINES: Record<Step, string> = {
  goals: "Bir vaqtda 3 tagacha yangi maqsad. Har biri o'z streak'iga ega bo'ladi — birida qoqilsangiz, boshqasi buzilmaydi.",
  runs: "Sizda allaqachon faol challenge'lar bor — ular ham kun tartibiga kiradi. Har vazifani qachon qilasiz? Bo'sh qoldirsangiz, vaqtni o'zim topaman.",
  day: "Kuningiz qanday o'tadi? Men vazifalarni faqat bo'sh vaqtingizga, bir-biriga to'qnashmasdan joylayman.",
  duration: "Qancha muddatga? Uzoqroq reja — oylik marralar bilan.",
};

type GoalDraft = { goal: string; current_level: string };

const hoursAndMinutes = (total: number) => `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;

export default function NewRoutine() {
  const router = useRouter();
  const toast = useToast();
  const { t } = useI18n();
  const { data: candidates } = useSWR<RoutineCandidate[]>("/me/routine/candidates");
  const [index, setIndex] = useState(0);
  const [runTimes, setRunTimes] = useState<Record<string, Record<string, string>>>({});
  const [goals, setGoals] = useState<GoalDraft[]>([{ goal: "", current_level: "" }]);
  const [wake, setWake] = useState("06:00");
  const [sleep, setSleep] = useState("23:00");
  const [busy, setBusy] = useState<BusyBlock[]>([]);
  const [duration, setDuration] = useState(60);
  const [loading, setLoading] = useState(false);

  const steps: Step[] = ["goals", ...(candidates?.length ? (["runs"] as const) : []), "day", "duration"];
  const step = steps[Math.min(index, steps.length - 1)];
  const last = index >= steps.length - 1;
  const filled = goals.filter((g) => g.goal.trim().length >= 3);
  const canNext = step === "goals" ? filled.length > 0 || Boolean(candidates?.length) : step === "day"
        ? wake < sleep && busy.every((b) => b.label.trim() && b.weekdays.length > 0 && b.start < b.end)
        : true;
  const runTime = (participationId: string, key: string, fallback: string | null) => runTimes[participationId]?.[key] ?? fallback ?? "";
  const setRunTime = (participationId: string, key: string, value: string) =>
    setRunTimes((all) => ({ ...all, [participationId]: { ...all[participationId], [key]: value } }));
  const patchGoal = (index: number, changes: Partial<GoalDraft>) => setGoals((all) => all.map((g, i) => (i === index ? { ...g, ...changes } : g)));
  const patchBlock = (index: number, changes: Partial<BusyBlock>) => setBusy((all) => all.map((b, i) => (i === index ? { ...b, ...changes } : b)));

  async function generate() {
    setLoading(true);
    try {
      const plan = await api<LifePlan>("/life-plans", {
        method: "POST",
        json: {
          goals: filled,
          wake,
          sleep,
          busy,
          duration_days: duration,
          runs: (candidates ?? []).map((c) => ({
            participation_id: c.participation_id,
            times: Object.fromEntries(c.tasks.map((task) => [task.key, runTime(c.participation_id, task.key, task.at) || null])),
          })),
        },
      });
      router.push(`/life-plans/${plan.id}`);
    } catch (error) {
      toast("error", errorMessage(error));
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex gap-1.5">
        {steps.map((_, i) => (
          <div key={i} className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
            <motion.div className="bg-flame h-full" initial={false} animate={{ width: i <= index ? "100%" : "0%" }} />
          </div>
        ))}
      </div>

      <div className="mb-6 flex items-start gap-3">
        <CoachAvatar />
        <div className="glass rounded-2xl rounded-tl-sm px-4 py-3 text-white/90">{t(COACH_LINES[step])}</div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} transition={{ duration: 0.25 }}>
          {step === "goals" && (
            <div className="flex flex-col gap-4">
              {goals.map((goal, index) => (
                <Card key={index} className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <Label>{t("{n}-maqsad", { n: index + 1 })}</Label>
                    {goals.length > 1 && (
                      <button onClick={() => setGoals((all) => all.filter((_, i) => i !== index))} className="p-1 text-mist hover:text-danger" aria-label={t("O'chirish")}>
                        <Trash2 className="size-4" />
                      </button>
                    )}
                  </div>
                  <Textarea
                    value={goal.goal}
                    onChange={(e) => patchGoal(index, { goal: e.target.value })}
                    placeholder={t("Masalan: 3 oyda backend dasturchi bo'lish")}
                    className="min-h-20"
                    autoFocus={index === 0}
                  />
                  <Input value={goal.current_level} onChange={(e) => patchGoal(index, { current_level: e.target.value })} placeholder={t("Hozirgi darajangiz (ixtiyoriy)")} />
                  {!goal.goal && (
                    <div className="flex flex-wrap gap-2">
                      {GOAL_IDEAS.map((idea) => (
                        <button key={idea} onClick={() => patchGoal(index, { goal: t(idea) })} className="rounded-xl bg-white/5 px-3 py-1.5 text-sm text-mist transition hover:bg-white/10 hover:text-white">
                          {t(idea)}
                        </button>
                      ))}
                    </div>
                  )}
                </Card>
              ))}
              {goals.length < MAX_GOALS && (
                <Button variant="secondary" onClick={() => setGoals((all) => [...all, { goal: "", current_level: "" }])}>
                  <Plus className="size-4" /> {t("Yana maqsad qo'shish")}
                </Button>
              )}
            </div>
          )}

          {step === "runs" && candidates && (
            <div className="flex flex-col gap-4">
              {candidates.map((run) => {
                const meta = CATEGORY[run.category];
                const Icon = meta.icon;
                return (
                  <Card key={run.participation_id} className="flex flex-col gap-3">
                    <div className="flex items-center gap-3">
                      <div className={`grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${meta.gradient}`}>
                        <Icon className="size-5" />
                      </div>
                      <p className="font-semibold">{run.title}</p>
                    </div>
                    {run.tasks.map((task) => (
                      <label key={task.key} className="flex items-center gap-3 rounded-2xl bg-ink-900/60 px-3 py-2">
                        <span className="min-w-0 flex-1 text-sm">
                          {task.title}
                          <span className="block text-xs text-mist">
                            {t("{m} daq", { m: task.minutes })} · {task.weekdays.length === 7 ? t("har kuni") : task.weekdays.map((d) => t(WEEKDAYS_SHORT[d])).join(", ")}
                          </span>
                        </span>
                        <input
                          type="time"
                          value={runTime(run.participation_id, task.key, task.at)}
                          onChange={(e) => setRunTime(run.participation_id, task.key, e.target.value)}
                          className="rounded-lg bg-white/5 px-2 py-1 text-sm tabular-nums [color-scheme:dark]"
                          aria-label={t("Boshlanish vaqti")}
                        />
                      </label>
                    ))}
                  </Card>
                );
              })}
            </div>
          )}

          {step === "day" && (
            <Card className="flex flex-col gap-5">
              <div className="grid grid-cols-2 gap-3">
                <label>
                  <Label>{t("Uyg'onish")}</Label>
                  <Input type="time" value={wake} onChange={(e) => setWake(e.target.value)} className="[color-scheme:dark]" />
                </label>
                <label>
                  <Label>{t("Uxlash")}</Label>
                  <Input type="time" value={sleep} onChange={(e) => setSleep(e.target.value)} className="[color-scheme:dark]" />
                </label>
              </div>

              <div>
                <Label hint={t("ish, o'qish, yo'l — reja bularni chetlab o'tadi")}>{t("Band vaqtlar")}</Label>
                <div className="flex flex-col gap-3">
                  {busy.map((block, index) => (
                    <div key={index} className="flex flex-col gap-2 rounded-2xl bg-ink-900/60 p-3">
                      <div className="flex items-center gap-2">
                        <input
                          value={block.label}
                          onChange={(e) => patchBlock(index, { label: e.target.value })}
                          maxLength={40}
                          autoFocus={!block.label}
                          placeholder={t("Nima qilasiz? Masalan: yo'l, sport zali")}
                          className="min-w-0 flex-1 bg-transparent px-1 text-sm font-semibold outline-none placeholder:font-normal placeholder:text-white/30"
                          aria-label={t("Nima qilasiz?")}
                        />
                        <input type="time" value={block.start} onChange={(e) => patchBlock(index, { start: e.target.value })} className="rounded-lg bg-white/5 px-2 py-1 text-sm tabular-nums [color-scheme:dark]" aria-label={t("Boshlanishi")} />
                        <span className="text-mist">–</span>
                        <input type="time" value={block.end} onChange={(e) => patchBlock(index, { end: e.target.value })} className="rounded-lg bg-white/5 px-2 py-1 text-sm tabular-nums [color-scheme:dark]" aria-label={t("Tugashi")} />
                        <button onClick={() => setBusy((all) => all.filter((_, i) => i !== index))} className="p-1 text-mist hover:text-danger" aria-label={t("O'chirish")}>
                          <Trash2 className="size-4" />
                        </button>
                      </div>
                      <div className="flex gap-1">
                        {WEEKDAYS_SHORT.map((day, weekday) => {
                          const on = block.weekdays.includes(weekday);
                          return (
                            <button
                              key={day}
                              onClick={() => patchBlock(index, { weekdays: on ? block.weekdays.filter((d) => d !== weekday) : [...block.weekdays, weekday].sort() })}
                              aria-pressed={on}
                              className={clsx("h-8 flex-1 rounded-lg text-xs font-semibold transition", on ? "bg-flame-500/25 text-flame-200" : "bg-white/5 text-mist hover:text-white")}
                            >
                              {t(day)}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                  <div className="flex flex-wrap gap-2">
                    {PRESETS.map((preset) => (
                      <button key={preset.label} onClick={() => setBusy((all) => [...all, { ...preset.block, label: t(preset.block.label) }])} className="rounded-xl bg-white/5 px-3 py-1.5 text-sm text-mist hover:bg-white/10 hover:text-white">
                        + {t(preset.label)}
                      </button>
                    ))}
                    <button onClick={() => setBusy((all) => [...all, { label: "", weekdays: [0, 1, 2, 3, 4], start: "09:00", end: "12:00" }])} className="rounded-xl bg-white/5 px-3 py-1.5 text-sm text-mist hover:bg-white/10 hover:text-white">
                      + {t("Boshqa")}
                    </button>
                  </div>
                </div>
              </div>

              <div>
                <Label hint={t("soat:daqiqa · rejaga 80% i ishlatiladi")}>{t("Bo'sh vaqtingiz")}</Label>
                <div className="grid grid-cols-7 gap-1 text-center text-xs">
                  {WEEKDAYS_SHORT.map((day, weekday) => (
                    <div key={day} className="rounded-xl bg-white/[0.03] px-1 py-2">
                      <p className="font-semibold">{t(day)}</p>
                      <p className="mt-1 text-mist tabular-nums">{hoursAndMinutes(freeMinutes(wake, sleep, busy, weekday))}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}

          {step === "duration" && (
            <div className="grid gap-3 sm:grid-cols-3">
              {DURATIONS.map((option) => (
                <button
                  key={option.days}
                  onClick={() => setDuration(option.days)}
                  aria-pressed={duration === option.days}
                  className={clsx(
                    "rounded-3xl border p-5 text-left transition",
                    duration === option.days ? "border-flame-500/60 bg-flame-500/10" : "border-white/10 bg-white/[0.02] hover:border-white/20",
                  )}
                >
                  <p className="font-display text-2xl font-bold">{t(option.title)}</p>
                  <p className="mt-2 text-sm text-mist">{t(option.body)}</p>
                </button>
              ))}
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      <div className="mt-6 flex justify-between gap-3">
        <Button variant="ghost" onClick={() => (index === 0 ? router.push("/onboarding") : setIndex((i) => i - 1))}>
          <ArrowLeft className="size-4" /> {t("Orqaga")}
        </Button>
        {!last ? (
          <Button disabled={!canNext} onClick={() => setIndex((i) => i + 1)}>
            {t("Keyingisi")} <ArrowRight className="size-4" />
          </Button>
        ) : (
          <Button loading={loading} onClick={generate}>
            <Sparkles className="size-4" /> {t("Kun tartibini tuzish")}
          </Button>
        )}
      </div>
      {loading && <p className="mt-4 text-center text-sm text-mist">{t("AI har bir maqsad uchun yo'l xaritasini yozmoqda — bir daqiqagacha vaqt oladi.")}</p>}
    </div>
  );
}
