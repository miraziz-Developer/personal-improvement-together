"use client";

import { BadgeCheck, LogOut, MapPin, Phone, Send } from "lucide-react";
import { useState } from "react";

import { OrDivider } from "@/components/AuthFields";
import { DataRights } from "@/components/DataRights";
import { TelegramCard } from "@/components/Telegram";
import { useToast } from "@/components/toast";
import { Badge, Button, Card, Input, Label, PageHeader, Skeleton, StreakFlame } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth, useFeatures } from "@/lib/auth";

export default function ProfilePage() {
  const { me, refreshMe, signOut } = useAuth();
  const { stakesEnabled, telegramBot, smsEnabled } = useFeatures();
  const toast = useToast();
  const [phone, setPhone] = useState("+998");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function request() {
    setLoading(true);
    try {
      await api("/auth/phone/request", { method: "POST", json: { phone } });
      setSent(true);
      toast("info", "Kod yuborildi", "SMS'dagi 6 xonali kodni kiriting.");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function confirm() {
    setLoading(true);
    try {
      await api("/auth/phone/confirm", { method: "POST", json: { code } });
      toast("success", "Telefon tasdiqlandi ✅");
      refreshMe();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  if (!me) return <Skeleton className="h-96" />;

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Profil" />
      <Card className="flex flex-col items-center gap-4 text-center sm:flex-row sm:text-left">
        <div className="bg-flame glow-flame grid size-20 place-items-center rounded-3xl font-display text-3xl font-bold uppercase">{me.username[0]}</div>
        <div className="flex-1">
          <h2 className="font-display text-2xl font-bold">{me.username}</h2>
          <div className="mt-2 flex flex-wrap justify-center gap-2 sm:justify-start">
            <Badge>
              <MapPin className="size-3.5" /> {me.region_name}
            </Badge>
            <Badge>{me.birth_year}-yil</Badge>
            {me.role !== "user" && <Badge className="text-iris">Moderator</Badge>}
          </div>
        </div>
        <div className="text-center">
          <StreakFlame streak={me.best_streak} size="lg" />
          <p className="text-xs text-mist">eng uzun streak</p>
        </div>
      </Card>

      <Card className="mt-6">
        <h3 className="flex items-center gap-2 font-semibold">
          <Phone className="size-4" /> Telefon raqam
        </h3>
        {me.phone_verified ? (
          <p className="mt-3 flex items-center gap-2 text-mint">
            <BadgeCheck className="size-5" /> {me.phone} tasdiqlangan
          </p>
        ) : (
          <div className="mt-4 flex flex-col gap-3">
            <p className="text-sm text-mist">
              {stakesEnabled ? "Garovli challenge'lar va parolni tiklash uchun kerak." : "Parolni tiklash va akkaunt xavfsizligi uchun kerak."} Bolalar
              ota-ona raqamidan foydalanishi mumkin.
            </p>
            {telegramBot && me.telegram_linked && (
              <>
                <Button href={`https://t.me/${telegramBot}?start=phone`} external variant="sky">
                  <Send className="size-4" /> Telegram orqali tasdiqlash
                </Button>
                <p className="text-center text-xs text-mist">
                  Botda «📱 Raqamni yuborish» tugmasini bosing — kod yozish shart emas. Qaytganingizda sahifa o'zi yangilanadi.
                </p>
              </>
            )}
            {telegramBot && !me.telegram_linked && (
              <p className="rounded-2xl bg-sky-500/10 p-3 text-sm text-sky-200">
                📲 Avval pastdagi <b>Telegram bot</b>ni ulang — raqamingizni u orqali bir bosishda, bepul tasdiqlaysiz.
              </p>
            )}
            {smsEnabled && (
              <div className="flex flex-col gap-3">
                {telegramBot && <OrDivider />}
                <label>
                  <Label>SMS orqali: raqam</Label>
                  <div className="flex gap-2">
                    <Input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" />
                    <Button variant="secondary" loading={loading && !sent} onClick={request}>
                      Kod olish
                    </Button>
                  </div>
                </label>
                {sent && (
                  <label>
                    <Label>SMS kod</Label>
                    <div className="flex gap-2">
                      <Input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" maxLength={6} placeholder="••••••" />
                      <Button loading={loading} onClick={confirm}>
                        Tasdiqlash
                      </Button>
                    </div>
                  </label>
                )}
              </div>
            )}
          </div>
        )}
      </Card>

      <TelegramCard />

      <DataRights />

      <Button variant="ghost" className="mt-6" onClick={signOut}>
        <LogOut className="size-4" /> Chiqish
      </Button>
    </div>
  );
}
