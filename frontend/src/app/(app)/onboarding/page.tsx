"use client";

import { ArrowRight, BookOpen, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

import { useI18n } from "@/lib/i18n";

/** "New goal" has exactly two doors: let the AI build the plan, or pick a ready one. */
export default function NewGoal() {
  const router = useRouter();
  const { t } = useI18n();

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="font-display text-3xl font-bold">{t("Yangi maqsad")}</h1>
      <p className="mt-2 text-mist">{t("Qaysi yo'l sizga qulay? Ikkalasi ham bugungi kun tartibingizga tushadi.")}</p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <button onClick={() => router.push("/routine/new")} className="glass group rounded-3xl p-6 text-left transition hover:border-flame-500/40">
          <div className="bg-flame glow-flame grid size-12 place-items-center rounded-2xl">
            <Sparkles className="size-6" />
          </div>
          <h2 className="mt-5 font-display text-xl font-semibold">{t("✨ AI menga reja tuzsin")}</h2>
          <p className="mt-2 text-mist">
            {t("Maqsadingizni (1–3 ta) va kuningiz qanday o'tishini ayting — AI har kun uchun soatma-soat reja va yo'l xaritasi tuzadi.")}
          </p>
          <ul className="mt-4 flex flex-col gap-1 text-sm text-white/80">
            <li>{t("• masalan: «backend dasturchi bo'lish», «5 kg massa olish»")}</li>
            <li>{t("• taxminan 1 daqiqa")}</li>
          </ul>
          <span className="mt-5 inline-flex items-center gap-1 font-semibold text-flame-400 group-hover:gap-2">
            {t("Boshlash")} <ArrowRight className="size-4 transition-all" />
          </span>
        </button>
        <button onClick={() => router.push("/routine?add=1")} className="glass group rounded-3xl p-6 text-left transition hover:border-white/25">
          <div className="grid size-12 place-items-center rounded-2xl bg-white/10">
            <BookOpen className="size-6" />
          </div>
          <h2 className="mt-5 font-display text-xl font-semibold">{t("📚 Tayyor challenge")}</h2>
          <p className="mt-2 text-mist">{t("Sinalgan dasturlardan birini tanlang (sport, kitob, kod, ingliz tili…) va qaysi soatda qilishingizni belgilang.")}</p>
          <ul className="mt-4 flex flex-col gap-1 text-sm text-white/80">
            <li>{t("• har kuni nima qilish aniq yozilgan")}</li>
            <li>{t("• 10 soniyada boshlanadi")}</li>
          </ul>
          <span className="mt-5 inline-flex items-center gap-1 font-semibold text-white/80 group-hover:gap-2">
            {t("Tanlash")} <ArrowRight className="size-4 transition-all" />
          </span>
        </button>
      </div>
    </div>
  );
}
