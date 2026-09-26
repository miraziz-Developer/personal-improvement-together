"use client";

import clsx from "clsx";
import { Camera, CheckCircle2, Clock, FileText, Loader2, RotateCcw, Upload, XCircle } from "lucide-react";
import { useRef, useState } from "react";

import { useToast } from "@/components/toast";
import { Badge, Button, Textarea } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { PROOF_STATUS } from "@/lib/format";
import type { TodayTask } from "@/lib/types";

const STATUS_ICON = { pending: Loader2, approved: CheckCircle2, rejected: XCircle, needs_review: Clock };

export function ProofTask({
  participationId,
  task,
  onSubmitted,
}: {
  participationId: string;
  task: TodayTask;
  onSubmitted: () => void;
}) {
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [open, setOpen] = useState(false);
  const [sending, setSending] = useState(false);

  const status = task.proof_status;
  const canSubmit = !status || status === "rejected";
  const Icon = status ? STATUS_ICON[status] : null;

  function pick(event: React.ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null;
    setFile(chosen);
    setPreview(chosen ? URL.createObjectURL(chosen) : null);
    setOpen(true);
  }

  async function submit() {
    if (!file && !note.trim()) {
      toast("info", "Rasm yoki qisqa matn qo'shing");
      return;
    }
    setSending(true);
    try {
      const form = new FormData();
      form.append("participation_id", participationId);
      form.append("task_key", task.key);
      if (note.trim()) form.append("text_note", note.trim());
      if (file) form.append("file", file);
      await api("/proofs", { method: "POST", body: form });
      toast("success", "Isbot yuborildi 📨", "Tekshiruvdan so'ng natijani ko'rasiz.");
      setFile(null);
      setPreview(null);
      setNote("");
      setOpen(false);
      onSubmitted();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className={clsx("rounded-3xl border p-4 transition", status === "approved" ? "border-mint/30 bg-mint/[0.06]" : "border-white/10 bg-white/[0.02]")}>
      <div className="flex items-start gap-3">
        <div className={clsx("grid size-10 shrink-0 place-items-center rounded-2xl", status === "approved" ? "bg-mint/20 text-mint" : "bg-white/5 text-mist")}>
          {Icon ? <Icon className={clsx("size-5", status === "pending" && "animate-spin")} /> : <Upload className="size-5" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold">{task.title}</p>
            <Badge>{task.minutes} daq</Badge>
            {!task.required && <Badge className="text-mist">qo'shimcha</Badge>}
          </div>
          {status && <p className={clsx("mt-1 text-sm font-medium", PROOF_STATUS[status].tone)}>{PROOF_STATUS[status].label}</p>}
          {status === "rejected" && task.reason && <p className="mt-1 text-sm text-mist">Sabab: {task.reason}. Qayta urinib ko'ring — hali vaqt bor 💪</p>}
        </div>
        {canSubmit && !open && (
          <Button size="sm" variant={status === "rejected" ? "secondary" : "primary"} onClick={() => setOpen(true)}>
            {status === "rejected" ? <RotateCcw className="size-4" /> : <Camera className="size-4" />}
            {status === "rejected" ? "Qayta" : "Isbot"}
          </Button>
        )}
      </div>

      {canSubmit && open && (
        <div className="mt-4 flex flex-col gap-3">
          <input ref={input} type="file" accept="image/*" capture="environment" className="hidden" onChange={pick} />
          <button
            onClick={() => input.current?.click()}
            className="relative grid min-h-36 place-items-center overflow-hidden rounded-2xl border border-dashed border-white/15 bg-ink-900/50 text-mist transition hover:border-flame-500/50"
          >
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="Tanlangan rasm" className="max-h-64 w-full object-cover" />
            ) : (
              <span className="flex flex-col items-center gap-2 text-sm">
                <Camera className="size-7" /> Rasm olish yoki tanlash
              </span>
            )}
          </button>
          <label className="flex items-center gap-2 text-sm text-mist">
            <FileText className="size-4" /> Qisqa izoh (ixtiyoriy)
          </label>
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Bugun nima qildingiz?" className="min-h-20" />
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Bekor
            </Button>
            <Button className="flex-1" loading={sending} onClick={submit}>
              Yuborish
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
