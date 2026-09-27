"use client";

import clsx from "clsx";
import confetti from "canvas-confetti";
import { CalendarClock, ChevronDown, Rocket } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { RoadmapView } from "@/components/Roadmap";
import { Timeline, type TimelineEntry } from "@/components/Timeline";
import { useToast } from "@/components/toast";
import { Badge, Button, Card, Segmented, Skeleton } from "@/components/ui";
import { WeekEditor } from "@/components/WeekEditor";
import { api, errorMessage } from "@/lib/api";
import { CATEGORY, WEEKDAYS_SHORT } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { LifeGoal, LifePlan, Week } from "@/lib/types";

function dayEntries(plan: LifePlan, weekday: number): TimelineEntry[] {
  const entries: TimelineEntry[] = [
    { kind: "wake", start: plan.wake, title: "" },
    ...plan.busy.filter((b) => b.weekdays.includes(weekday)).map((b) => ({ kind: "busy" as const, start: b.start, end: b.end, title: b.label })),
    ...plan.goals.flatMap((goal) =>
      goal.week[weekday].map((task) => ({
        kind: "task" as const,
        start: task.at ?? "",
        title: task.title,
        category: goal.category,
        goal: goal.title,
        minutes: task.minutes,
        optional: !task.required,
      })),
    ),
    { kind: "sleep", start: plan.sleep, title: "" },
  ];
  const order = { wake: 0, busy: 1, task: 2, sleep: 3 };
  return entries.sort((a, b) => a.start.localeCompare(b.start) || order[a.kind] - order[b.kind]);
}

function GoalCard({ plan, goal, onSaved }: { plan: LifePlan; goal: LifeGoal; onSaved: (plan: LifePlan) => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [edited, setEdited] = useState<Week | null>(null);
  const [saving, setSaving] = useState(false);
  const meta = CATEGORY[goal.category];
  const Icon = meta.icon;
  const draft = plan.status === "draft";

  async function save() {
    setSaving(true);
    try {
      onSaved(await api<LifePlan>(`/life-plans/${plan.id}/goals/${goal.key}`, { method: "PUT", json: { week: edited } }));
      setEdited(null);
      toast("success", t("Reja saqlandi"));
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="flex flex-col gap-4">
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex items-start gap-4 text-left">
        <div className={`grid size-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${meta.gradient}`}>
          <Icon className="size-6" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-display text-lg font-semibold">{goal.title}</p>
          <p className="mt-1 line-clamp-2 text-sm text-mist">{goal.description}</p>
        </div>
        <ChevronDown className={clsx("mt-1 size-5 shrink-0 text-mist transition", open && "rotate-180")} />
      </button>
      {open && (
        <>
          {draft && (
            <>
              <WeekEditor week={edited ?? goal.week} onChange={setEdited} />
              {edited && (
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={() => setEdited(null)}>
                    {t("Bekor")}
                  </Button>
                  <Button className="flex-1" loading={saving} onClick={save}>
                    {t("Saqlash")}
                  </Button>
                </div>
              )}
            </>
          )}
          {goal.roadmap && <RoadmapView roadmap={goal.roadmap} />}
        </>
      )}
    </Card>
  );
}

export default function LifePlanPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { t } = useI18n();
  const { data: plan, mutate } = useSWR<LifePlan>(`/life-plans/${id}`);
  const [weekday, setWeekday] = useState(() => (new Date().getDay() + 6) % 7);
  const [starting, setStarting] = useState(false);

  if (!plan) return <Skeleton className="h-96" />;

  async function start() {
    setStarting(true);
    try {
      await api(`/life-plans/${id}/start`, { method: "POST" });
      confetti({ particleCount: 160, spread: 90, origin: { y: 0.7 }, colors: ["#ff9a3d", "#ff5f3a", "#ff3d7f", "#7c5cff"] });
      toast("success", t("Kun tartibi boshlandi! 🚀"), t("Har bir maqsad — o'z challenge'i va o'z streak'i."));
      router.push("/routine");
    } catch (error) {
      toast("error", errorMessage(error));
      setStarting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <Badge className="mb-3">
          <CalendarClock className="size-3.5" /> {t("Kun tartibi")} · {t("{n} kun", { n: plan.duration_days })}
        </Badge>
        <h1 className="font-display text-2xl font-bold sm:text-3xl">{plan.status === "draft" ? t("Kun tartibingiz tayyor ✨") : t("Sizning kun tartibingiz")}</h1>
        <p className="mt-2 text-mist">{t("Hamma maqsadlar bitta kunga, bir-biriga to'qnashmasdan joylandi. Vaqtni o'zgartirsangiz, to'qnashuvni o'zim tekshiraman.")}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {plan.goals.map((goal) => (
            <Badge key={goal.key}>{goal.title}</Badge>
          ))}
        </div>
      </Card>

      <Card>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-lg font-semibold">{t("Kun bo'yicha")}</h2>
          <Segmented<string> value={String(weekday)} onChange={(v) => setWeekday(Number(v))} options={WEEKDAYS_SHORT.map((day, i) => ({ value: String(i), label: t(day) }))} />
        </div>
        <Timeline entries={dayEntries(plan, weekday)} />
      </Card>

      <div className="flex flex-col gap-4">
        <h2 className="font-display text-lg font-semibold">{t("Maqsadlar")}</h2>
        {plan.goals.map((goal) => (
          <GoalCard key={goal.key} plan={plan} goal={goal} onSaved={(updated) => mutate(updated, false)} />
        ))}
      </div>

      {plan.status === "draft" ? (
        <Button size="lg" loading={starting} onClick={start}>
          <Rocket className="size-5" /> {t("Hammasini boshlash")}
        </Button>
      ) : (
        <Button size="lg" href="/routine">
          {t("Bugungi kun tartibi")}
        </Button>
      )}
    </div>
  );
}
