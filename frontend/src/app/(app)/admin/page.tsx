"use client";

import { CheckCircle2, Coins, Flag, XCircle } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { useToast } from "@/components/toast";
import { Badge, Button, Card, EmptyState, PageHeader, Skeleton, Textarea } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { money, shortDate } from "@/lib/format";
import type { ReportItem, ReportReason, ReviewItem } from "@/lib/types";

function ReviewCard({ item, onDone }: { item: ReviewItem; onDone: () => void }) {
  const toast = useToast();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [revealed, setRevealed] = useState(false); // spare moderators from harmful images by default

  async function decide(approved: boolean) {
    if (!approved && !note.trim()) {
      toast("info", "Rad etish sababini yozing", "Foydalanuvchi uni ko'radi.");
      return;
    }
    setBusy(approved ? "approve" : "reject");
    try {
      await api(`/admin/proofs/${item.proof_id}/review`, { method: "POST", json: { approved, note } });
      toast("success", approved ? "Tasdiqlandi" : "Rad etildi");
      onDone();
    } catch (error) {
      toast("error", errorMessage(error));
      setBusy(null);
    }
  }

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-semibold">{item.username}</p>
        <Badge>{item.challenge_title}</Badge>
        <Badge>{item.task_key}</Badge>
        <Badge>{shortDate(item.for_date)}</Badge>
        {item.flagged && <Badge className="border-danger/40 bg-danger/15 text-danger">⚠️ Nomaqbul kontent shubhasi</Badge>}
        {item.stake > 0 && (
          <Badge className="text-amberish">
            <Coins className="size-3" /> {money(item.stake)}
          </Badge>
        )}
      </div>
      {item.image_url && (
        <div className="relative">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={item.image_url}
            alt="Isbot"
            className={`max-h-96 w-full rounded-2xl bg-black/30 object-contain transition ${item.flagged && !revealed ? "blur-2xl" : ""}`}
          />
          {item.flagged && !revealed && (
            <button onClick={() => setRevealed(true)} className="absolute inset-0 grid place-items-center text-sm font-semibold">
              Rasm yashirilgan — ko'rsatish
            </button>
          )}
        </div>
      )}
      {item.text_note && <p className="rounded-2xl bg-white/[0.03] p-3 text-sm">{item.text_note}</p>}
      {item.ai_reason && (
        <p className="text-sm text-mist">
          AI: {item.ai_reason} {item.ai_confidence !== null && `(ishonch ${Math.round(item.ai_confidence * 100)}%)`}
        </p>
      )}
      <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Izoh (rad etishda majburiy)" className="min-h-16" />
      <div className="flex gap-2">
        <Button variant="danger" className="flex-1" loading={busy === "reject"} onClick={() => decide(false)}>
          <XCircle className="size-4" /> Rad etish
        </Button>
        <Button className="flex-1" loading={busy === "approve"} onClick={() => decide(true)}>
          <CheckCircle2 className="size-4" /> Tasdiqlash
        </Button>
      </div>
    </Card>
  );
}

const REASON_LABEL: Record<ReportReason, string> = {
  abuse: "Haqorat",
  bad_name: "Nomaqbul username",
  spam: "Spam",
  other: "Boshqa",
};

function ReportsSection() {
  const toast = useToast();
  const { data, mutate } = useSWR<ReportItem[]>("/admin/reports", { refreshInterval: 30_000 });

  async function resolve(report: ReportItem, action: "dismiss" | "reset_username") {
    try {
      await api(`/admin/reports/${report.id}/resolve`, { method: "POST", json: { action } });
      toast("success", action === "dismiss" ? "Shikoyat yopildi" : `${report.reported} username'i tozalandi`);
      mutate();
    } catch (error) {
      toast("error", errorMessage(error));
    }
  }

  return (
    <section className="mt-10">
      <h2 className="flex items-center gap-2 font-display text-xl font-semibold">
        <Flag className="size-5 text-danger" /> Shikoyatlar
      </h2>
      {data?.length === 0 && <p className="mt-3 text-sm text-mist">Ochiq shikoyat yo'q ✨</p>}
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {data?.map((report) => (
          <Card key={report.id} className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold">{report.reported}</p>
              <Badge className="border-danger/40 text-danger">{REASON_LABEL[report.reason]}</Badge>
              {report.reports_against > 1 && <Badge>{report.reports_against} ta shikoyat</Badge>}
            </div>
            <p className="text-sm text-mist">
              {report.reporter} · {shortDate(report.created_at)}
            </p>
            {report.details && <p className="rounded-2xl bg-white/[0.03] p-3 text-sm">{report.details}</p>}
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" onClick={() => resolve(report, "dismiss")}>
                Rad etish
              </Button>
              <Button size="sm" variant="danger" onClick={() => resolve(report, "reset_username")}>
                Username'ni tozalash
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}

export default function AdminPage() {
  const toast = useToast();
  const { data, mutate, error } = useSWR<ReviewItem[]>("/admin/proofs", { refreshInterval: 15_000 });

  async function run(path: string, label: string) {
    try {
      const result = await api<Record<string, number>>(path, { method: "POST" });
      toast("success", label, JSON.stringify(result));
    } catch (e) {
      toast("error", errorMessage(e));
    }
  }

  if (error) return <EmptyState icon="🔒" title="Ruxsat yo'q" body={errorMessage(error)} />;

  return (
    <div>
      <PageHeader
        title="Moderator paneli"
        subtitle="Shubhali isbotlar. Pulli challenge'lar birinchi — adolatli va tez qaror qiling."
        action={
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => run("/admin/jobs/close-days", "Kunlar yopildi")}>
              Kunlarni yopish
            </Button>
            <Button size="sm" variant="secondary" onClick={() => run("/admin/jobs/nudges/evening", "Eslatmalar yuborildi")}>
              Kechki eslatma
            </Button>
          </div>
        }
      />
      {!data && <Skeleton className="h-64" />}
      {data?.length === 0 && <EmptyState icon="✨" title="Navbat bo'sh" body="Hozircha tekshirishga isbot yo'q." />}
      <div className="grid gap-4 lg:grid-cols-2">
        {data?.map((item) => (
          <ReviewCard key={item.proof_id} item={item} onDone={() => mutate()} />
        ))}
      </div>
      <ReportsSection />
    </div>
  );
}
