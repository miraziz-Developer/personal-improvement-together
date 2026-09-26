"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useToast } from "@/components/toast";
import { Button, Input, Label } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const toast = useToast();
  const { t } = useI18n();
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function requestCode(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      await api("/auth/password/forgot", { method: "POST", json: { username } });
      setSent(true);
      toast("info", t("Kod yuborildi"), t("Telegram botga (ulangan bo'lsa) yoki tasdiqlangan telefonga SMS keladi."));
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function reset(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      await api("/auth/password/reset", { method: "POST", json: { username, code, new_password: password } });
      toast("success", t("Parol yangilandi ✅"), t("Endi yangi parol bilan kiring."));
      router.push("/login");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={sent ? reset : requestCode} className="flex flex-col gap-5">
      <div>
        <h1 className="font-display text-3xl font-bold">{t("Parolni tiklash 🔑")}</h1>
        <p className="mt-2 text-mist">{t("Kodni Telegram botga yuboramiz. Bot ulanmagan bo'lsa — tasdiqlangan raqamga SMS.")}</p>
      </div>
      <label>
        <Label>Username</Label>
        <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required disabled={sent} />
      </label>
      {sent && (
        <>
          <label>
            <Label>{t("Tasdiqlash kodi")}</Label>
            <Input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" maxLength={6} placeholder="••••••" required />
          </label>
          <label>
            <Label hint={t("8+ belgi, harf va raqam")}>{t("Yangi parol")}</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required />
          </label>
        </>
      )}
      <Button type="submit" size="lg" loading={loading}>
        {sent ? t("Parolni yangilash") : t("Kod olish")}
      </Button>
      <p className="text-center text-mist">
        {t("Esladingizmi?")}{" "}
        <Link href="/login" className="font-semibold text-flame-400 hover:text-flame-300">
          {t("Kirish")}
        </Link>
      </p>
    </form>
  );
}
