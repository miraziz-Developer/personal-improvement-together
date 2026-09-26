"use client";

import clsx from "clsx";
import { AlertTriangle, Coins, Gift, Rocket } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button, Card } from "@/components/ui";
import { useAuth, useFeatures } from "@/lib/auth";
import { money } from "@/lib/format";
import type { Mode } from "@/lib/types";

const QUICK = [20_000, 50_000, 100_000, 200_000];

export function StartPanel({
  stakeAllowed,
  minStake = 10_000,
  maxStake = 2_000_000,
  loading,
  onStart,
}: {
  stakeAllowed: boolean;
  minStake?: number;
  maxStake?: number;
  loading: boolean;
  onStart: (mode: Mode, amount: number) => void;
}) {
  const { me } = useAuth();
  const { stakesEnabled } = useFeatures();
  const [mode, setMode] = useState<Mode>("free");
  const [amount, setAmount] = useState(50_000);
  const available = me?.wallet.available ?? 0;
  const invalid = mode === "stake" && (amount < minStake || amount > maxStake);

  if (!stakesEnabled) {
    return (
      <Card>
        <div className="flex items-start gap-3 rounded-2xl bg-mint/[0.07] p-4">
          <Gift className="mt-0.5 size-5 shrink-0 text-mint" />
          <div>
            <p className="font-semibold">Hozircha hammasi bepul 🎁</p>
            <p className="mt-1 text-sm text-mist">Ball, streak, reyting va murabbiy — barchasi siz uchun ochiq.</p>
          </div>
        </div>
        <Button size="lg" className="mt-5 w-full" loading={loading} onClick={() => onStart("free", 0)}>
          Boshlash 🚀
        </Button>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="font-display text-lg font-semibold">Qanday boshlaymiz?</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {(
          [
            ["free", "Oddiy", "Ball, streak va reyting uchun", Rocket],
            ["stake", "Garov bilan", "Pul muzlatiladi, bajarsangiz 100% qaytadi", Coins],
          ] as const
        ).map(([value, title, body, Icon]) => (
          <button
            key={value}
            disabled={value === "stake" && !stakeAllowed}
            onClick={() => setMode(value)}
            className={clsx(
              "rounded-2xl border p-4 text-left transition disabled:opacity-40",
              mode === value ? "border-flame-500/60 bg-flame-500/10" : "border-white/10 bg-white/[0.02] hover:border-white/20",
            )}
          >
            <Icon className={clsx("size-5", mode === value ? "text-flame-400" : "text-mist")} />
            <p className="mt-2 font-semibold">{title}</p>
            <p className="mt-1 text-sm text-mist">{value === "stake" && !stakeAllowed ? "Bu challenge uchun mavjud emas" : body}</p>
          </button>
        ))}
      </div>

      {mode === "stake" && (
        <div className="mt-5 flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            {QUICK.map((q) => (
              <button
                key={q}
                onClick={() => setAmount(q)}
                className={clsx(
                  "rounded-xl px-3 py-1.5 text-sm font-semibold transition",
                  amount === q ? "bg-flame text-white" : "bg-white/5 text-mist hover:text-white",
                )}
              >
                {money(q)}
              </button>
            ))}
          </div>
          <input type="range" min={minStake} max={Math.min(maxStake, 500_000)} step={5_000} value={amount} onChange={(e) => setAmount(Number(e.target.value))} />
          <p className="font-display text-2xl font-bold">{money(amount)}</p>
          <p className="text-sm leading-relaxed text-mist">
            Challenge oxirigacha bajarilsa, garov to'liq qaytadi. Bajarilmasa — platformada qoladi. Pul hech qachon faqat AI qarori bilan kuymaydi:
            shubhali holatlarni inson tekshiradi.
          </p>
          {!me?.phone_verified && (
            <p className="flex items-start gap-2 rounded-2xl bg-amberish/10 p-3 text-sm text-amberish">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span>
                Avval telefon raqamingizni <Link href="/profile" className="font-semibold underline">tasdiqlang</Link>.
              </span>
            </p>
          )}
          {me && available < amount && (
            <p className="flex items-start gap-2 rounded-2xl bg-white/5 p-3 text-sm text-mist">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span>
                Hamyonda {money(available)} bor. <Link href="/wallet" className="font-semibold text-flame-400 underline">Hisobni to'ldiring</Link>.
              </span>
            </p>
          )}
        </div>
      )}

      <Button size="lg" className="mt-6 w-full" loading={loading} disabled={invalid} onClick={() => onStart(mode, mode === "stake" ? amount : 0)}>
        {mode === "stake" ? `${money(amount)} bilan boshlash` : "Boshlash"} 🚀
      </Button>
    </Card>
  );
}
