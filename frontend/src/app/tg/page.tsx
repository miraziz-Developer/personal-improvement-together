"use client";

import { useRouter } from "next/navigation";
import Script from "next/script";
import { useCallback, useRef, useState } from "react";

import { Logo } from "@/components/AppShell";
import { GOOGLE_SIGNUP_KEY, type GoogleSignup } from "@/components/GoogleButton";
import { Button, Spinner } from "@/components/ui";
import { api, errorMessage, tokenStore } from "@/lib/api";
import { safeNext, useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { TELEGRAM_SCRIPT, telegramApp } from "@/lib/telegram";

type TelegramOut = { access_token: string | null; signup_token: string | null; suggested_username: string | null };

const BACKGROUND = "#06060b"; // --color-ink-950: Telegram's frame matches the app

/** The bot's "📱 Open the app" lands here: Telegram vouches for the user, no password. */
export default function TelegramEntry() {
  const { signIn } = useAuth();
  const { t } = useI18n();
  const router = useRouter();
  const started = useRef(false);
  const [signup, setSignup] = useState<GoogleSignup | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const next = useCallback(() => safeNext(new URLSearchParams(window.location.search).get("next")) ?? "/routine", []);

  const enter = useCallback(async () => {
    const app = telegramApp();
    if (!app) {
      router.replace(next()); // opened in an ordinary browser
      return;
    }
    app.ready();
    app.expand();
    app.setHeaderColor?.(BACKGROUND);
    app.setBackgroundColor?.(BACKGROUND);
    app.disableVerticalSwipes?.();
    setProblem(null);
    try {
      const out = await api<TelegramOut>("/auth/telegram", { method: "POST", json: { init_data: app.initData } });
      if (out.access_token) {
        signIn(out.access_token);
        router.replace(next());
      } else if (tokenStore.get()) {
        // Signed in on this device already: this Telegram chat now follows the account.
        await api("/me/telegram/webapp", { method: "POST", json: { init_data: app.initData } });
        router.replace(next());
      } else {
        setSignup({ token: out.signup_token ?? "", email: null, username: out.suggested_username ?? "", next: next(), provider: "telegram" });
      }
    } catch (error) {
      setProblem(errorMessage(error));
    }
  }, [router, signIn, next]);

  function start() {
    if (started.current) return;
    started.current = true;
    void enter();
  }

  function create() {
    if (!signup) return;
    sessionStorage.setItem(GOOGLE_SIGNUP_KEY, JSON.stringify(signup));
    router.push("/register/google");
  }

  return (
    <main className="grid min-h-dvh place-items-center px-6 py-10">
      <Script src={TELEGRAM_SCRIPT} strategy="afterInteractive" onReady={start} onError={() => router.replace(next())} />
      <div className="flex w-full max-w-sm flex-col items-center gap-6 text-center">
        <Logo />
        {problem ? (
          <>
            <p className="text-danger">{problem}</p>
            <Button onClick={() => void enter()}>{t("Qayta urinish")}</Button>
          </>
        ) : signup ? (
          <>
            <div>
              <h1 className="font-display text-2xl font-bold">{t("Xush kelibsiz! 👋")}</h1>
              <p className="mt-2 text-mist">{t("PIT — maqsadlaringizni har kungi odatga aylantiradigan murabbiy. Telegram'ingiz bilan bir daqiqada boshlaysiz.")}</p>
            </div>
            <Button size="lg" className="w-full" onClick={create}>
              {t("Yangi akkaunt ochish")}
            </Button>
            <Button variant="ghost" className="w-full" href={`/login?next=${encodeURIComponent(`/tg?next=${signup.next}`)}`}>
              {t("Saytda akkauntim bor — kirish")}
            </Button>
          </>
        ) : (
          <>
            <Spinner className="size-8" />
            <p className="text-mist">{t("Kirilmoqda…")}</p>
          </>
        )}
      </div>
    </main>
  );
}
