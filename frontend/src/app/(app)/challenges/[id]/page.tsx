"use client";

import confetti from "canvas-confetti";
import { ArrowLeft, CalendarDays, Camera, Users } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { StartPanel } from "@/components/StartPanel";
import { useToast } from "@/components/toast";
import { Badge, Card, Skeleton } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { CATEGORY, WEEKDAYS, minutes } from "@/lib/format";
import type { Challenge, Mode } from "@/lib/types";

export default function ChallengeDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { data: c } = useSWR<Challenge>(`/challenges/${id}`);
  const [loading, setLoading] = useState(false);

  async function join(mode: Mode, amount: number) {
    setLoading(true);
    try {
      const { id: pid } = await api<{ id: string }>(`/challenges/${id}/join`, { method: "POST", json: { mode, stake_amount: amount } });
      confetti({ particleCount: 140, spread: 80, origin: { y: 0.75 }, colors: ["#ff9a3d", "#ff5f3a", "#ff3d7f", "#34e8a8"] });
      toast("success", "Qo'shildingiz! 🚀", "Bugundan boshlab har kuni bir qadam.");
      router.push(`/c/${pid}`);
    } catch (error) {
      toast("error", errorMessage(error));
      setLoading(false);
    }
  }

  if (!c) return <Skeleton className="h-96" />;
  const meta = CATEGORY[c.category];
  const Icon = meta.icon;

  return (
    <div className="flex flex-col gap-6">
      <Link href="/challenges" className="inline-flex items-center gap-1 text-sm text-mist hover:text-white">
        <ArrowLeft className="size-4" /> Katalog
      </Link>
      <div className={`relative overflow-hidden rounded-3xl bg-gradient-to-br ${meta.gradient} p-6 sm:p-10`}>
        <Icon className="absolute -right-6 -bottom-6 size-48 text-white/15" />
        <Badge className="border-white/20 bg-black/20 text-white">{meta.label}</Badge>
        <h1 className="mt-4 max-w-xl font-display text-3xl font-bold sm:text-4xl">{c.title}</h1>
        <p className="mt-3 max-w-xl text-white/85">{c.description}</p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Badge className="border-white/20 bg-black/20 text-white">
            <CalendarDays className="size-3.5" /> {c.duration_days} kun
          </Badge>
          <Badge className="border-white/20 bg-black/20 text-white">{minutes(c.minutes_per_week)} / hafta</Badge>
          <Badge className="border-white/20 bg-black/20 text-white">
            <Users className="size-3.5" /> {c.participants} ishtirokchi
          </Badge>
          <Badge className="border-white/20 bg-black/20 text-white">
            <Camera className="size-3.5" /> {c.proof_types.includes("text") ? "rasm yoki matn" : "rasm"}
          </Badge>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <Card>
          <h2 className="font-display text-lg font-semibold">Haftalik reja</h2>
          <div className="mt-4 flex flex-col gap-2">
            {c.week.map((tasks, day) => (
              <div key={day} className="flex items-start gap-4 rounded-2xl bg-white/[0.03] px-4 py-3">
                <span className="w-24 shrink-0 text-sm font-semibold">{WEEKDAYS[day]}</span>
                {tasks.length ? (
                  <div className="flex flex-wrap gap-1.5">
                    {tasks.map((t) => (
                      <Badge key={t.key} className={t.required ? "" : "text-mist"}>
                        {t.title} · {t.minutes} daq{!t.required && " (qo'shimcha)"}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <span className="text-sm text-mist">Dam olish 🌿</span>
                )}
              </div>
            ))}
          </div>
        </Card>
        <StartPanel stakeAllowed={c.stake_allowed} minStake={c.min_stake} maxStake={c.max_stake} loading={loading} onStart={join} />
      </div>
    </div>
  );
}
