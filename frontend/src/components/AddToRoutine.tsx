"use client";

import { ArrowLeft, Clock } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { useToast } from "@/components/toast";
import { Button, Modal, Skeleton } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { CATEGORY, minutes, WEEKDAYS_SHORT } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { type FrameLike, timeProblem, toMinutes } from "@/lib/routine";
import type { Challenge, Participation } from "@/lib/types";

type TaskLine = { key: string; title: string; minutes: number; weekdays: number[]; at?: string | null };

/** The challenge's tasks once each, with the days they happen on. */
function taskLines(challenge: Challenge): TaskLine[] {
  const lines = new Map<string, TaskLine>();
  challenge.week.forEach((day, weekday) =>
    day.forEach((task) => {
      const line = lines.get(task.key);
      if (line) line.weekdays.push(weekday);
      else lines.set(task.key, { key: task.key, title: task.title, minutes: task.minutes, weekdays: [weekday], at: task.at });
    }),
  );
  return Array.from(lines.values());
}

/** "I'll do this challenge at this time": pick a challenge, give its tasks times, done. */
/** Two picked tasks of the same challenge that would overlap on a shared day. */
function selfClash(lines: TaskLine[], times: Record<string, string>): Record<string, string> {
  const clashes: Record<string, string> = {};
  for (const a of lines) {
    for (const b of lines) {
      if (a.key === b.key || !times[a.key] || !times[b.key] || !a.weekdays.some((d) => b.weekdays.includes(d))) continue;
      const [aStart, bStart] = [toMinutes(times[a.key]), toMinutes(times[b.key])];
      if (aStart < bStart + b.minutes && bStart < aStart + a.minutes) clashes[a.key] = b.title;
    }
  }
  return clashes;
}

export function AddToRoutine({
  open,
  onClose,
  onAdded,
  frame,
}: {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
  frame?: FrameLike | null;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { data: catalog } = useSWR<Challenge[]>(open ? "/challenges" : null);
  const { data: mine } = useSWR<Participation[]>(open ? "/me/participations" : null);
  const [picked, setPicked] = useState<Challenge | null>(null);
  const [times, setTimes] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const lines = picked ? taskLines(picked) : [];
  const clashes = selfClash(lines, times);
  const problems = Object.fromEntries(
    lines.map((task) => {
      const problem = timeProblem(frame, times[task.key] ?? "", task.minutes, task.weekdays);
      if (problem) return [task.key, t(problem[0], problem[1])];
      if (clashes[task.key]) return [task.key, t("«{title}» bilan ustma-ust", { title: clashes[task.key] })];
      return [task.key, null];
    }),
  );
  const blocked = Object.values(problems).some(Boolean);
  const running = new Set(mine?.filter((p) => p.status === "active" || p.status === "scheduled").map((p) => p.challenge_id));
  const available = catalog?.filter((c) => !running.has(c.id)) ?? [];

  function pick(challenge: Challenge) {
    setPicked(challenge);
    // A time that is the point of the task ("rise by 06:30") comes filled in.
    setTimes(Object.fromEntries(taskLines(challenge).flatMap((line) => (line.at ? [[line.key, line.at]] : []))));
  }

  function close() {
    setPicked(null);
    setTimes({});
    onClose();
  }

  async function add() {
    if (!picked) return;
    setSaving(true);
    try {
      await api("/me/routine/challenges", {
        method: "POST",
        json: { challenge_id: picked.id, times: Object.fromEntries(Object.entries(times).filter(([, at]) => at)) },
      });
      toast("success", t("Kun tartibiga qo'shildi 🎉"), picked.title);
      onAdded();
      close();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={close} title={picked ? picked.title : t("Kun tartibiga challenge qo'shish")}>
      {!picked ? (
        <div className="flex max-h-[60vh] flex-col gap-2 overflow-y-auto">
          {!catalog && [0, 1, 2].map((i) => <Skeleton key={i} className="h-16" />)}
          {catalog && available.length === 0 && <p className="text-sm text-mist">{t("Katalogdagi hamma challenge'larda allaqachon qatnashyapsiz 💪")}</p>}
          {available.map((challenge) => {
            const meta = CATEGORY[challenge.category];
            const days = challenge.week.filter((day) => day.length > 0).length;
            const perDay = Math.round(challenge.minutes_per_week / Math.max(days, 1));
            const Icon = meta.icon;
            return (
              <button
                key={challenge.id}
                onClick={() => pick(challenge)}
                className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.02] p-3 text-left transition hover:border-white/25"
              >
                <div className={`grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${meta.gradient}`}>
                  <Icon className="size-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold">{challenge.title}</p>
                  <p className="text-xs text-mist">
                    {t("{n} kun", { n: challenge.duration_days })} · {t("kuniga ~{time}", { time: minutes(perDay) })}
                    {days < 7 && ` · ${t("haftada {d} kun", { d: days })}`}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-mist">{t("Har vazifani qachon qilasiz? Bo'sh qoldirsangiz, bo'sh vaqtingizdan o'zim joy topaman.")}</p>
          {lines.map((task) => (
            <label key={task.key} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-2xl bg-ink-900/60 px-3 py-2">
              <span className="min-w-0 flex-1 text-sm">
                {task.title}
                <span className="block text-xs text-mist">
                  {t("{m} daq", { m: task.minutes })} ·{" "}
                  {task.weekdays.length === 7 ? t("har kuni") : task.weekdays.map((d) => t(WEEKDAYS_SHORT[d])).join(", ")}
                </span>
              </span>
              <span className="flex items-center gap-1.5 rounded-xl bg-white/5 px-2 py-1 text-xs text-mist focus-within:text-white">
                <Clock className="size-3.5" />
                <input
                  type="time"
                  value={times[task.key] ?? ""}
                  onChange={(e) => setTimes((all) => ({ ...all, [task.key]: e.target.value }))}
                  className="bg-transparent tabular-nums outline-none [color-scheme:dark]"
                  aria-label={t("Boshlanish vaqti")}
                />
              </span>
              {problems[task.key] && <span className="w-full text-xs text-danger">{problems[task.key]}</span>}
            </label>
          ))}
          <div className="mt-2 flex gap-2">
            <Button variant="ghost" onClick={() => setPicked(null)}>
              <ArrowLeft className="size-4" /> {t("Orqaga")}
            </Button>
            <Button className="flex-1" loading={saving} disabled={blocked} onClick={add}>
              {t("Kun tartibiga qo'shish")}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
