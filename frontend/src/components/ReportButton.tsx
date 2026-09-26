"use client";

import clsx from "clsx";
import { Flag } from "lucide-react";
import { useState } from "react";

import { useToast } from "@/components/toast";
import { Button, Modal, Textarea } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import type { ReportReason } from "@/lib/types";

const REASONS: [ReportReason, string][] = [
  ["abuse", "Haqorat yoki bezorilik"],
  ["bad_name", "Nomaqbul username"],
  ["spam", "Spam"],
  ["other", "Boshqa"],
];

/** A quiet flag next to someone's name; a moderator reads every report. */
export function ReportButton({ username }: { username: string }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<ReportReason>("abuse");
  const [details, setDetails] = useState("");
  const [sending, setSending] = useState(false);

  async function send() {
    setSending(true);
    try {
      await api("/reports", { method: "POST", json: { username, reason, details } });
      toast("success", "Shikoyat yuborildi", "Moderator ko'rib chiqadi. Rahmat, jamiyatni toza saqlashga yordam berdingiz.");
      setOpen(false);
      setDetails("");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button onClick={() => setOpen(true)} aria-label={`${username} haqida shikoyat`} className="rounded-lg p-1 text-mist/60 transition hover:text-danger">
        <Flag className="size-3.5" />
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title={`${username} haqida shikoyat`}>
        <div className="flex flex-col gap-2">
          {REASONS.map(([value, label]) => (
            <button
              key={value}
              onClick={() => setReason(value)}
              className={clsx(
                "rounded-2xl border px-4 py-3 text-left text-sm transition",
                reason === value ? "border-danger/50 bg-danger/10" : "border-white/10 bg-white/[0.02] hover:border-white/20",
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <Textarea className="mt-4" value={details} onChange={(e) => setDetails(e.target.value)} maxLength={500} placeholder="Nima bo'ldi? (ixtiyoriy)" />
        <Button variant="danger" className="mt-4 w-full" loading={sending} onClick={send}>
          Yuborish
        </Button>
      </Modal>
    </>
  );
}
