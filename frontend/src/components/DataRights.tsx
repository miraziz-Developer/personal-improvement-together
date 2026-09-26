"use client";

import { Download, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useToast } from "@/components/toast";
import { Button, Card, Input, Label, Modal } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Profile: take a copy of your data, or erase the account for good. */
export function DataRights() {
  const { me, signOut } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [exporting, setExporting] = useState(false);
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [erasing, setErasing] = useState(false);

  if (!me) return null;

  async function download() {
    setExporting(true);
    try {
      const data = await api<unknown>("/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `pit-${me?.username}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
      toast("success", "Yuklab olindi", "Rasm havolalari 15 daqiqa ishlaydi — kerak bo'lsa, hozir saqlab oling.");
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setExporting(false);
    }
  }

  async function erase() {
    setErasing(true);
    try {
      await api("/me", { method: "DELETE", json: { username: confirm } });
      signOut();
      toast("info", "Akkaunt o'chirildi", "Sizni yana kutib qolamiz. O'zingizga yaxshi qarang 🌱");
      router.push("/");
    } catch (error) {
      toast("error", errorMessage(error));
      setErasing(false);
    }
  }

  return (
    <Card className="mt-6">
      <h3 className="font-semibold">Ma'lumotlarim</h3>
      <p className="mt-1 text-sm text-mist">
        Ma'lumotlaringiz sizniki: nusxasini oling yoki akkauntni butunlay o'chiring.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="secondary" size="sm" loading={exporting} onClick={download}>
          <Download className="size-4" /> Nusxasini yuklab olish
        </Button>
        <Button variant="danger" size="sm" onClick={() => setOpen(true)}>
          <Trash2 className="size-4" /> Akkauntni o'chirish
        </Button>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Akkauntni o'chirasizmi?">
        <ul className="flex flex-col gap-1.5 text-sm text-white/85">
          <li>🗑 Username, telefon, email, Google va Telegram ulanishi o'chiriladi</li>
          <li>📸 Barcha isbot rasmlari va yozuvlaringiz o'chiriladi</li>
          <li>🏆 Reytingdan chiqasiz, faol challenge'lar yopiladi</li>
          <li>⚠️ Buni qaytarib bo'lmaydi</li>
        </ul>
        <label className="mt-5 block">
          <Label>
            Tasdiqlash uchun <b className="text-white">{me.username}</b> deb yozing
          </Label>
          <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" />
        </label>
        <div className="mt-6 flex gap-2">
          <Button variant="secondary" className="flex-1" onClick={() => setOpen(false)}>
            Qolaman
          </Button>
          <Button variant="danger" className="flex-1" loading={erasing} disabled={confirm.trim().toLowerCase() !== me.username} onClick={erase}>
            O'chirish
          </Button>
        </div>
      </Modal>
    </Card>
  );
}
