"use client";

import { ArrowDownLeft, ArrowUpRight, Lock, LockOpen, Wallet as WalletIcon } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { useToast } from "@/components/toast";
import { Button, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth, useFeatures } from "@/lib/auth";
import { money, timeAgo } from "@/lib/format";
import type { Wallet } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const KINDS: Record<string, { label: string; sign: string; icon: React.ElementType; tone: string }> = {
  deposit: { label: "Hisob to'ldirildi", sign: "+", icon: ArrowDownLeft, tone: "text-mint" },
  withdrawal: { label: "Yechib olindi", sign: "−", icon: ArrowUpRight, tone: "text-white" },
  stake_lock: { label: "Garov muzlatildi", sign: "", icon: Lock, tone: "text-amberish" },
  stake_release: { label: "Garov qaytarildi 🎉", sign: "+", icon: LockOpen, tone: "text-mint" },
  stake_forfeit: { label: "Garov platformaga o'tdi", sign: "−", icon: Lock, tone: "text-danger" },
};

export default function WalletPage() {
  const toast = useToast();
  const { t } = useI18n();
  const { refreshMe } = useAuth();
  const { stakesEnabled } = useFeatures();
  const { data, mutate } = useSWR<Wallet>(stakesEnabled ? "/wallet" : null);
  const [loading, setLoading] = useState<number | null>(null);

  async function deposit(amount: number) {
    setLoading(amount);
    try {
      await api("/wallet/dev-deposit", { method: "POST", json: { amount } });
      toast("success", t("{sum} qo'shildi", { sum: money(amount) }));
      mutate();
      refreshMe();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(null);
    }
  }

  if (!stakesEnabled) {
    return (
      <Card>
        <EmptyState
          icon="🎁"
          title={t("Hozircha hammasi bepul")}
          body={t("Garov rejimi va hamyon keyinroq ochiladi. Hozir esa odatlaringizga e'tibor bering!")}
        />
      </Card>
    );
  }

  return (
    <div>
      <PageHeader title={t("Hamyon")} subtitle={t("Garov — o'zingizga bergan va'daning kafolati.")} />
      {!data ? (
        <Skeleton className="h-64" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
          <div className="flex flex-col gap-4">
            <div className="bg-flame glow-flame relative overflow-hidden rounded-3xl p-6">
              <WalletIcon className="absolute -right-4 -bottom-4 size-32 text-white/15" />
              <p className="text-sm text-white/80">{t("Mavjud balans")}</p>
              <p className="mt-2 font-display text-4xl font-bold">{money(data.available)}</p>
              <p className="mt-4 flex items-center gap-2 text-sm text-white/85">
                <Lock className="size-4" /> {t("Muzlatilgan: {sum}", { sum: money(data.locked) })}
              </p>
            </div>
            <Card>
              <h3 className="font-semibold">{t("Hisobni to'ldirish")}</h3>
              <p className="mt-1 text-sm text-mist">{t("Test rejimi: pul darhol qo'shiladi. Ishga tushganda Payme / Click orqali bo'ladi.")}</p>
              <div className="mt-4 grid grid-cols-3 gap-2">
                {[50_000, 100_000, 200_000].map((amount) => (
                  <Button key={amount} variant="secondary" size="sm" loading={loading === amount} onClick={() => deposit(amount)}>
                    +{amount / 1000}k
                  </Button>
                ))}
              </div>
            </Card>
          </div>
          <Card>
            <h3 className="mb-3 font-semibold">{t("Tarix")}</h3>
            {data.transactions.length === 0 ? (
              <EmptyState icon="🧾" title={t("Hali operatsiya yo'q")} body={t("Garovli challenge boshlaganingizda bu yerda ko'rinadi.")} />
            ) : (
              <div className="flex flex-col gap-1">
                {data.transactions.map((tx) => {
                  const kind = KINDS[tx.kind] ?? KINDS.deposit;
                  const Icon = kind.icon;
                  return (
                    <div key={tx.id} className="flex items-center gap-3 rounded-2xl px-3 py-3 hover:bg-white/[0.03]">
                      <div className="grid size-10 place-items-center rounded-xl bg-white/5">
                        <Icon className={`size-5 ${kind.tone}`} />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium">{t(kind.label)}</p>
                        <p className="text-xs text-mist">{timeAgo(tx.created_at)}</p>
                      </div>
                      <p className={`font-semibold tabular-nums ${kind.tone}`}>
                        {kind.sign}
                        {money(tx.amount)}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
