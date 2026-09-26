"use client";

import { BadgeCheck, BellRing, Camera, ExternalLink, Send, Sun } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useToast } from "@/components/toast";
import { Button, Card } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth, useFeatures } from "@/lib/auth";

const PERKS = [
  { icon: Sun, text: "Ertalab — bugungi reja" },
  { icon: BellRing, text: "Kechqurun — bajarilmagan vazifalar" },
  { icon: Camera, text: "Isbotni bir bosishda yuborish" },
];

/** Profile: connect or disconnect the Telegram bot. Hidden while no bot is configured. */
export function TelegramCard() {
  const { me, refreshMe } = useAuth();
  const { telegramBot } = useFeatures();
  const toast = useToast();
  const [link, setLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const linked = me?.telegram_linked ?? false;

  // While the user presses Start in Telegram, check every few seconds whether it went through.
  useEffect(() => {
    if (!link || linked) return;
    const timer = setInterval(() => refreshMe(), 3000);
    return () => clearInterval(timer);
  }, [link, linked, refreshMe]);

  if (!telegramBot || !me) return null;

  async function connect() {
    setLoading(true);
    try {
      const { url } = await api<{ url: string }>("/me/telegram", { method: "POST" });
      setLink(url);
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function disconnect() {
    setLoading(true);
    try {
      await api("/me/telegram", { method: "DELETE" });
      setLink(null);
      await refreshMe();
      toast("info", "Telegram uzildi", "Eslatmalar endi faqat saytda ko'rinadi.");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="relative mt-6 overflow-hidden">
      <div className="absolute -top-16 -right-16 size-40 rounded-full bg-sky-500/20 blur-3xl" />
      <h3 className="relative flex items-center gap-2 font-semibold">
        <Send className="size-4 text-sky-400" /> Telegram bot
      </h3>
      {linked ? (
        <div className="relative mt-3 flex flex-wrap items-center justify-between gap-3">
          <p className="flex items-center gap-2 text-mint">
            <BadgeCheck className="size-5" /> Ulangan — murabbiy Telegram'da yozadi
          </p>
          <div className="flex gap-2">
            <Button href={`https://t.me/${telegramBot}`} external variant="secondary" size="sm">
              Botni ochish <ExternalLink className="size-3.5" />
            </Button>
            <Button variant="ghost" size="sm" loading={loading} onClick={disconnect}>
              Uzish
            </Button>
          </div>
        </div>
      ) : (
        <div className="relative mt-4 flex flex-col gap-4">
          <ul className="grid gap-2 sm:grid-cols-3">
            {PERKS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2 rounded-2xl bg-white/[0.03] px-3 py-2.5 text-sm text-white/85">
                <Icon className="size-4 shrink-0 text-sky-400" />
                {text}
              </li>
            ))}
          </ul>
          {link ? (
            <div className="flex flex-col gap-2">
              <Button href={link} external variant="sky" size="lg">
                Telegram'da ochish <ExternalLink className="size-4" />
              </Button>
              <p className="text-center text-sm text-mist">
                Telegram'da <b className="text-white">Start</b> ni bosing — shu sahifa o'zi yangilanadi. Havola 10 daqiqa amal qiladi.
              </p>
            </div>
          ) : (
            <Button variant="sky" size="lg" loading={loading} onClick={connect}>
              <Send className="size-4" /> Telegram'ni ulash
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}

/** Dashboard: a small invitation until the bot is connected. */
export function TelegramNudge() {
  const { me } = useAuth();
  const { telegramBot } = useFeatures();
  if (!telegramBot || !me || me.telegram_linked) return null;
  return (
    <Link href="/profile" className="glass group flex items-center gap-4 rounded-3xl p-4 transition hover:border-sky-400/40">
      <div className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sky-500/15">
        <Send className="size-5 text-sky-400" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-semibold">Eslatmalarni Telegram'da oling</p>
        <p className="text-sm text-mist">Isbotni ham botning o'zida yuborasiz 📸</p>
      </div>
      <span className="text-sky-400 transition group-hover:translate-x-1">→</span>
    </Link>
  );
}
