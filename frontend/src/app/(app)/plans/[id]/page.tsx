"use client";

import confetti from "canvas-confetti";
import { CalendarDays, Gauge, ShieldCheck } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { StartPanel } from "@/components/StartPanel";
import { useToast } from "@/components/toast";
import { Badge, Button, Card, Skeleton } from "@/components/ui";
import { WeekEditor } from "@/components/WeekEditor";
import { api, errorMessage } from "@/lib/api";
import { CATEGORY, minutes } from "@/lib/format";
import type { Mode, Plan, Week } from "@/lib/types";

export default function PlanPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { data: plan, mutate } = useSWR<Plan>(`/plans/${id}`);
  const [edited, setWeek] = useState<Week | null>(null);
  const week = edited ?? plan?.week ?? null;
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);

  if (!plan || !week) return <Skeleton className="h-96" />;
  const meta = CATEGORY[plan.category];
  const Icon = meta.icon;
  const dirty = JSON.stringify(week) !== JSON.stringify(plan.week);
  const weekly = week.flat().filter((t) => t.required).reduce((s, t) => s + t.minutes, 0);
  const days = week.filter((d) => d.length).length;

  async function save() {
    setSaving(true);
    try {
      await mutate(await api<Plan>(`/plans/${id}/schedule`, { method: "PUT", json: { week } }), false);
      toast("success", "Reja saqlandi");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function start(mode: Mode, amount: number) {
    setStarting(true);
    try {
      if (dirty) await api(`/plans/${id}/schedule`, { method: "PUT", json: { week } });
      const { id: participationId } = await api<{ id: string }>(`/plans/${id}/start`, {
        method: "POST",
        json: { mode, stake_amount: amount },
      });
      confetti({ particleCount: 160, spread: 90, origin: { y: 0.7 }, colors: ["#ff9a3d", "#ff5f3a", "#ff3d7f", "#7c5cff"] });
      toast("success", "Sayohat boshlandi! 🚀", "Birinchi qadam — eng muhimi. Siz uni qo'ydingiz.");
      router.push(`/c/${participationId}`);
    } catch (error) {
      toast("error", errorMessage(error));
      setStarting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card className="relative overflow-hidden">
        <div className={`absolute -top-20 -right-20 size-64 rounded-full bg-gradient-to-br ${meta.gradient} opacity-20 blur-3xl`} />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className={`grid size-16 shrink-0 place-items-center rounded-3xl bg-gradient-to-br ${meta.gradient}`}>
            <Icon className="size-8" />
          </div>
          <div>
            <Badge className="mb-2">✨ Siz uchun tuzilgan reja</Badge>
            <h1 className="font-display text-2xl font-bold">{plan.title}</h1>
            <p className="mt-1 text-mist">{plan.description}</p>
          </div>
        </div>
        <div className="relative mt-5 flex flex-wrap gap-2">
          <Badge>
            <CalendarDays className="size-3.5" /> {plan.duration_days} kun
          </Badge>
          <Badge>
            <Gauge className="size-3.5" /> Qiyinlik {plan.difficulty}/5
          </Badge>
          <Badge>
            {days} kun/hafta · {minutes(weekly)} majburiy
          </Badge>
          <Badge>
            <ShieldCheck className="size-3.5" /> {plan.verification_prompt}
          </Badge>
        </div>
      </Card>

      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-lg font-semibold">Haftalik reja</h2>
          <p className="text-sm text-mist">Istalgancha o'zgartiring. Chiziq — bo'sh vaqtingizning 80% i.</p>
        </div>
        {plan.status === "draft" && dirty && (
          <Button size="sm" variant="secondary" loading={saving} onClick={save}>
            Saqlash
          </Button>
        )}
      </div>
      <WeekEditor week={week} budgets={plan.budgets} onChange={setWeek} />

      {plan.status === "draft" ? (
        <StartPanel stakeAllowed loading={starting} onStart={start} />
      ) : (
        plan.participation_id && (
          <Button href={`/c/${plan.participation_id}`} size="lg">
            Challenge sahifasiga o'tish
          </Button>
        )
      )}
    </div>
  );
}
