"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, useSyncExternalStore } from "react";

import { RegionSelect, TermsConsent } from "@/components/AuthFields";
import { GOOGLE_SIGNUP_KEY, type GoogleSignup } from "@/components/GoogleButton";
import { useToast } from "@/components/toast";
import { Button, Input, Label } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { safeNext, useAuth, useFeatures } from "@/lib/auth";

const noSubscription = () => () => {};

function readSignup(): string | null {
  try {
    return sessionStorage.getItem(GOOGLE_SIGNUP_KEY);
  } catch {
    return null;
  }
}

/** After "Continue with Google" for a new account: Google gives no birth date or region. */
export default function GoogleRegisterPage() {
  const raw = useSyncExternalStore(noSubscription, readSignup, () => null);
  const signup = useMemo(() => (raw ? (JSON.parse(raw) as GoogleSignup) : null), [raw]);
  const { signIn } = useAuth();
  const { termsVersion } = useFeatures();
  const router = useRouter();
  const toast = useToast();
  const [username, setUsername] = useState<string | null>(null);
  const [birthDate, setBirthDate] = useState("");
  const [regionId, setRegionId] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!signup) {
    return (
      <div className="flex flex-col gap-4 text-center">
        <h1 className="font-display text-2xl font-bold">Sessiya topilmadi</h1>
        <p className="text-mist">Google orqali qaytadan kiring — bu bir soniya oladi.</p>
        <Button href="/register">Ro'yxatdan o'tish</Button>
      </div>
    );
  }
  const name = username ?? signup.username;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!signup) return;
    setLoading(true);
    try {
      const { access_token } = await api<{ access_token: string }>("/auth/google/register", {
        method: "POST",
        json: {
          signup_token: signup.token,
          username: name,
          birth_date: birthDate,
          region_id: regionId,
          accepted_terms_version: agreed ? termsVersion : "",
        },
      });
      sessionStorage.removeItem(GOOGLE_SIGNUP_KEY);
      signIn(access_token);
      toast("success", "Xush kelibsiz! 🎉", "Keling, birinchi maqsadingizni belgilaymiz.");
      router.push(safeNext(signup.next) ?? "/onboarding");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      <div>
        <h1 className="font-display text-3xl font-bold">Oxirgi qadam ✨</h1>
        <p className="mt-2 text-mist">
          {signup.email ? <b className="text-white">{signup.email}</b> : "Google akkauntingiz"} ulandi. Reyting uchun yoshingiz va hududingiz kerak.
        </p>
      </div>
      <label>
        <Label hint="lotin harflari, raqam, _">Username</Label>
        <Input value={name} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <Label hint="7 yoshdan">Tug'ilgan sana</Label>
          <Input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} required />
        </label>
        <label>
          <Label>Hudud</Label>
          <RegionSelect value={regionId} onChange={setRegionId} />
        </label>
      </div>
      <TermsConsent checked={agreed} onChange={setAgreed} />
      <Button type="submit" size="lg" loading={loading} disabled={!agreed || !termsVersion}>
        Boshlash 🚀
      </Button>
      <p className="text-center text-sm text-mist">
        Boshqa akkaunt?{" "}
        <Link href="/login" className="font-semibold text-flame-400 hover:text-flame-300">
          Kirish
        </Link>
      </p>
    </form>
  );
}
