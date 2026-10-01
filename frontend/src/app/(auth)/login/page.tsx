"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { GoogleButton } from "@/components/GoogleButton";
import { useToast } from "@/components/toast";
import { Button, Input, Label } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { safeNext, useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

function LoginForm() {
  const { signIn } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next")) ?? "/routine";
  const toast = useToast();
  const { t } = useI18n();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      const { access_token } = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        json: { username, password },
      });
      signIn(access_token);
      router.push(next);
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      <div>
        <h1 className="font-display text-3xl font-bold">{t("Qaytganingizdan xursandmiz 👋")}</h1>
        <p className="mt-2 text-mist">{t("Streak'ingiz sizni kutyapti.")}</p>
      </div>
      <GoogleButton next={next} />
      <label>
        <Label>Username</Label>
        <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
      </label>
      <label>
        <Label>{t("Parol")}</Label>
        <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
      </label>
      <Link href="/forgot" className="-mt-2 self-end text-sm text-mist hover:text-white">
        {t("Parolni unutdingizmi?")}
      </Link>
      <Button type="submit" size="lg" loading={loading}>
        {t("Kirish")}
      </Button>
      <p className="text-center text-mist">
        {t("Akkauntingiz yo'qmi?")}{" "}
        <Link href={next === "/routine" ? "/register" : `/register?next=${encodeURIComponent(next)}`} className="font-semibold text-flame-400 hover:text-flame-300">
          {t("Ro'yxatdan o'ting")}
        </Link>
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
