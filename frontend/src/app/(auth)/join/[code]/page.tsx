"use client";

import { Users } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { useToast } from "@/components/toast";
import { Badge, Button, Skeleton } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CATEGORY, minutes } from "@/lib/format";
import type { GroupPreview } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

/** Where an invite link lands — for people with or without an account. */
export default function JoinPage() {
  const { code } = useParams<{ code: string }>();
  const { token } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const { t, tx } = useI18n();
  const { data, error } = useSWR<GroupPreview>(`/groups/${code}`);
  const [joining, setJoining] = useState(false);
  const here = `/join/${code}`;

  async function join() {
    setJoining(true);
    try {
      const { id } = await api<{ id: string }>(`/groups/${code}/join`, { method: "POST" });
      toast("success", t("Guruhga qo'shildingiz! 🤝"), t("Bugundan birga boshlaymiz."));
      router.push(`/c/${id}`);
    } catch (err) {
      toast("error", errorMessage(err));
    } finally {
      setJoining(false);
    }
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4 text-center">
        <h1 className="font-display text-2xl font-bold">{t("Havola ishlamayapti 😕")}</h1>
        <p className="text-mist">{errorMessage(error)}</p>
        <Button href="/">{t("Bosh sahifa")}</Button>
      </div>
    );
  }
  if (!data) return <Skeleton className="h-96" />;

  const meta = CATEGORY[data.category];
  const Icon = meta.icon;
  const days = data.week.filter((day) => day.length > 0).length;
  const weekly = data.week.flat().reduce((sum, task) => sum + task.minutes, 0);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Badge className="border-flame-500/30 bg-flame-500/10 text-flame-300">
          <Users className="size-3.5" /> {t("Taklif")}
        </Badge>
        <h1 className="mt-4 font-display text-3xl font-bold">
          {tx("{owner} sizni birga challenge'ga chaqiryapti", { owner: <span className="text-flame">{data.owner}</span> })}
        </h1>
      </div>

      <div className="glass rounded-3xl p-5">
        <div className="flex items-start gap-4">
          <div className={`grid size-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br ${meta.gradient}`}>
            <Icon className="size-6" />
          </div>
          <div className="min-w-0">
            <p className="font-display text-lg font-semibold">{data.challenge_title}</p>
            <p className="mt-1 line-clamp-3 text-sm text-mist">{data.challenge_description}</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-1.5">
          <Badge>{t("{n} kun", { n: data.duration_days })}</Badge>
          <Badge>{t("Haftada {n} kun", { n: days })}</Badge>
          <Badge>{t("{time}/hafta", { time: minutes(weekly) })}</Badge>
          <Badge>
            <Users className="size-3.5" /> {t("{n} kishi", { n: data.members })}
          </Badge>
        </div>
      </div>

      <ul className="flex flex-col gap-2 text-sm text-white/85">
        <li>{t("🤝 Hammangiz bir xil reja bo'yicha harakat qilasiz")}</li>
        <li>{t("🔥 Kim bugun bajarganini guruhda ko'rib turasiz")}</li>
        <li>{t("📲 Do'stingiz bajarsa, murabbiy sizga ham xabar beradi")}</li>
      </ul>

      {token ? (
        <Button size="lg" loading={joining} onClick={join}>
          {t("Qo'shilish va boshlash 🚀")}
        </Button>
      ) : (
        <div className="flex flex-col gap-3">
          <Button href={`/register?next=${encodeURIComponent(here)}`} size="lg">
            {t("Ro'yxatdan o'tib qo'shilish 🚀")}
          </Button>
          <Button href={`/login?next=${encodeURIComponent(here)}`} variant="secondary">
            {t("Akkauntim bor — kirish")}
          </Button>
        </div>
      )}
    </div>
  );
}
