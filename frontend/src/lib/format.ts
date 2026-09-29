import {
  BookOpen,
  Code2,
  Dumbbell,
  GraduationCap,
  HeartPulse,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import { currentLocale, type Locale, translate } from "./i18n";
import type { Category, DayStatus, ProofStatus } from "./types";

export const WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"];
export const WEEKDAYS_SHORT = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
const MONTHS: Record<Locale, string[]> = {
  uz: ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"],
  ru: ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
};

// These build sentences outside React, so they read the current language themselves.
const t = (text: string, values?: Record<string, string | number>) => translate(currentLocale(), text, values);

export function money(amount: number): string {
  return `${Math.round(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ")} ${t("so'm")}`;
}

export function shortDate(iso: string): string {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  const locale = currentLocale();
  const month = MONTHS[locale][d.getMonth()];
  return locale === "ru" ? `${d.getDate()} ${month}` : `${d.getDate()}-${month}`;
}

export function minutes(total: number): string {
  if (total < 60) return t("{m} daq", { m: total });
  const h = Math.floor(total / 60);
  const m = total % 60;
  return m ? t("{h} soat {m} daq", { h, m }) : t("{h} soat", { h });
}

export function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return t("hozirgina");
  if (seconds < 3600) return t("{n} daqiqa oldin", { n: Math.floor(seconds / 60) });
  if (seconds < 86400) return t("{n} soat oldin", { n: Math.floor(seconds / 3600) });
  return t("{n} kun oldin", { n: Math.floor(seconds / 86400) });
}

export function greeting(name: string): string {
  const hour = new Date().getHours();
  if (hour < 5) return t("Tun bo'yi bedormisiz, {name}? 🌙", { name });
  if (hour < 12) return t("Xayrli tong, {name} ☀️", { name });
  if (hour < 18) return t("Xayrli kun, {name} 👋", { name });
  return t("Xayrli kech, {name} 🌆", { name });
}

export const CATEGORY: Record<Category, { label: string; icon: LucideIcon; gradient: string }> = {
  sport: { label: "Sport", icon: Dumbbell, gradient: "from-orange-500 to-rose-500" },
  code: { label: "Dasturlash", icon: Code2, gradient: "from-violet-500 to-indigo-500" },
  reading: { label: "Kitob", icon: BookOpen, gradient: "from-amber-400 to-orange-500" },
  study: { label: "O'qish", icon: GraduationCap, gradient: "from-sky-400 to-blue-600" },
  health: { label: "Sog'liq", icon: HeartPulse, gradient: "from-emerald-400 to-teal-500" },
  custom: { label: "Shaxsiy", icon: Sparkles, gradient: "from-fuchsia-500 to-pink-500" },
};

export const DAY_STATUS: Record<DayStatus, { label: string; cell: string; dot: string }> = {
  done: { label: "Bajarildi", cell: "bg-mint/80 shadow-[0_0_12px_rgb(52_232_168/0.45)]", dot: "bg-mint" },
  frozen: { label: "Freeze", cell: "bg-ice/60", dot: "bg-ice" },
  missed: { label: "O'tkazildi", cell: "bg-danger/70", dot: "bg-danger" },
  awaiting_review: { label: "Kutilmoqda", cell: "bg-amberish/70", dot: "bg-amberish" },
  pending: { label: "Oldinda", cell: "bg-white/[0.07]", dot: "bg-white/30" },
  paused: { label: "Pauza", cell: "bg-iris/40", dot: "bg-iris" },
};

export const PROOF_STATUS: Record<ProofStatus, { label: string; tone: string }> = {
  pending: { label: "Tekshirilmoqda…", tone: "text-amberish" },
  approved: { label: "Tasdiqlandi", tone: "text-mint" },
  rejected: { label: "Qabul qilinmadi", tone: "text-danger" },
  needs_review: { label: "Moderator ko'rmoqda", tone: "text-ice" },
};

export const STATUS_LABEL: Record<string, string> = {
  scheduled: "Boshlanishini kutmoqda",
  active: "Faol",
  completed: "Yakunlandi 🏆",
  failed: "Yakunlanmadi",
  cancelled: "Bekor qilindi",
};
