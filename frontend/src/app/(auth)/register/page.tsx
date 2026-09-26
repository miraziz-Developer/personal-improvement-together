"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { RegionSelect, TermsConsent } from "@/components/AuthFields";
import { GoogleButton } from "@/components/GoogleButton";
import { useToast } from "@/components/toast";
import { Button, Input, Label } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { safeNext, useAuth, useFeatures } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

function RegisterForm() {
  const { signIn } = useAuth();
  const router = useRouter();
  // From an invite link: come back to it after signing up instead of onboarding.
  const next = safeNext(useSearchParams().get("next"));
  const toast = useToast();
  const { t } = useI18n();
  const [form, setForm] = useState({ username: "", password: "", birth_date: "", region_id: "" });
  const [loading, setLoading] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const { termsVersion } = useFeatures();
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const strong = form.password.length >= 8 && /\d/.test(form.password) && /\D/.test(form.password);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      const { access_token } = await api<{ access_token: string }>("/auth/register", {
        method: "POST",
        json: { ...form, accepted_terms_version: agreed ? termsVersion : "" },
      });
      signIn(access_token);
      toast("success", t("Xush kelibsiz! 🎉"), t("Keling, birinchi maqsadingizni belgilaymiz."));
      router.push(next ?? "/onboarding");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      <div>
        <h1 className="font-display text-3xl font-bold">{t("Yangi boshlanish ✨")}</h1>
        <p className="mt-2 text-mist">{t("1 daqiqa — va sizning sayohatingiz boshlanadi.")}</p>
      </div>
      <GoogleButton next={next ?? "/onboarding"} />
      <label>
        <Label hint={t("lotin harflari, raqam, _")}>Username</Label>
        <Input value={form.username} onChange={set("username")} placeholder={t("masalan: ali_2008")} autoComplete="username" required />
      </label>
      <label>
        <Label hint={form.password ? t(strong ? "✓ yaxshi parol" : "8+ belgi, harf va raqam") : undefined}>{t("Parol")}</Label>
        <Input type="password" value={form.password} onChange={set("password")} autoComplete="new-password" required />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <Label hint={t("7 yoshdan")}>{t("Tug'ilgan sana")}</Label>
          <Input type="date" value={form.birth_date} onChange={set("birth_date")} required />
        </label>
        <label>
          <Label>{t("Hudud")}</Label>
          <RegionSelect value={form.region_id} onChange={(region_id) => setForm((f) => ({ ...f, region_id }))} />
        </label>
      </div>
      <TermsConsent checked={agreed} onChange={setAgreed} />
      <Button type="submit" size="lg" loading={loading} disabled={!agreed || !termsVersion}>
        {t("Boshlash 🚀")}
      </Button>
      <p className="text-center text-mist">
        {t("Akkauntingiz bormi?")}{" "}
        <Link href={next ? `/login?next=${encodeURIComponent(next)}` : "/login"} className="font-semibold text-flame-400 hover:text-flame-300">
          {t("Kirish")}
        </Link>
      </p>
    </form>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
