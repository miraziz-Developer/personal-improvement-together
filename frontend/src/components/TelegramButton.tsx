"use client";

import { Send } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { OrDivider } from "@/components/AuthFields";
import { GOOGLE_SIGNUP_KEY, type GoogleSignup } from "@/components/GoogleButton";
import { useToast } from "@/components/toast";
import { Button } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth, useFeatures } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { telegramApp } from "@/lib/telegram";

type Started = { token: string; url: string };
type Outcome = { access_token: string | null; signup_token: string | null; suggested_username: string | null; pending: boolean };

const POLL_MS = 2000;

/** "Sign in with Telegram": the bot opens, Start confirms the chat, this page signs in. */
export function TelegramButton({ next = "/routine" }: { next?: string }) {
  const { telegramBot, googleClientId } = useFeatures();
  const { signIn } = useAuth();
  const { t } = useI18n();
  const router = useRouter();
  const toast = useToast();
  const [waiting, setWaiting] = useState<Started | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(async () => {
      try {
        const out = await api<Outcome>("/auth/telegram/login/check", { method: "POST", json: { token: waiting.token } });
        if (out.pending) return;
        clearInterval(timer);
        setWaiting(null);
        if (out.access_token) {
          signIn(out.access_token);
          router.push(next);
          return;
        }
        const signup: GoogleSignup = { token: out.signup_token ?? "", email: null, username: out.suggested_username ?? "", next, provider: "telegram" };
        sessionStorage.setItem(GOOGLE_SIGNUP_KEY, JSON.stringify(signup));
        router.push("/register/google");
      } catch (error) {
        clearInterval(timer);
        setWaiting(null);
        toast("error", errorMessage(error));
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [waiting, signIn, router, next, toast]);

  // Inside Telegram the app signs in by itself (/tg); there is nothing to press.
  if (!telegramBot || telegramApp()) return null;

  async function start() {
    // Opened right away, in the click itself, so the browser does not block the new tab.
    const tab = window.open("", "_blank");
    setStarting(true);
    try {
      const started = await api<Started>("/auth/telegram/login", { method: "POST" });
      if (tab) tab.location.href = started.url;
      setWaiting(started);
    } catch (error) {
      tab?.close();
      toast("error", errorMessage(error));
    } finally {
      setStarting(false);
    }
  }

  return (
    <>
      {waiting ? (
        <div className="flex flex-col items-center gap-2 rounded-2xl border border-sky-400/30 bg-sky-400/[0.06] p-4 text-center">
          <p className="text-sm">{t("Telegram'da botni oching va «Start» ni bosing — shu sahifa o'zi kiradi.")}</p>
          <div className="flex gap-2">
            <Button size="sm" href={waiting.url} external>
              <Send className="size-4" /> {t("Telegram'ni ochish")}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setWaiting(null)}>
              {t("Bekor qilish")}
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="secondary" className="w-full" loading={starting} onClick={start}>
          <Send className="size-4 text-sky-400" /> {t("Telegram orqali kirish")}
        </Button>
      )}
      {!googleClientId && <OrDivider />}
    </>
  );
}
