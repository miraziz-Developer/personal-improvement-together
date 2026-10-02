"use client";

import { BellRing } from "lucide-react";
import { useState } from "react";

import { useToast } from "@/components/toast";
import { Button, Card, Input, Label } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { NotificationPrefs } from "@/lib/types";

const LEADS = [0, 5, 10, 15, 30];
const hhmm = (value: string | null) => (value ? value.slice(0, 5) : null);

/** How the coach may reach me: the heads-up before a task, quiet hours, friends' news. */
export function NotificationSettings({ prefs }: { prefs: NotificationPrefs }) {
  const { refreshMe } = useAuth();
  const { t } = useI18n();
  const toast = useToast();
  const [lead, setLead] = useState(prefs.remind_before);
  const [quiet, setQuiet] = useState(prefs.quiet_from !== null);
  const [from, setFrom] = useState(hhmm(prefs.quiet_from) ?? "23:00");
  const [to, setTo] = useState(hhmm(prefs.quiet_to) ?? "07:00");
  const [friends, setFriends] = useState(prefs.friends_news);
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await api("/me/notifications/settings", {
        method: "PUT",
        json: { remind_before: lead, quiet_from: quiet ? from : null, quiet_to: quiet ? to : null, friends_news: friends },
      });
      await refreshMe();
      toast("success", t("Eslatma sozlamalari saqlandi"));
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="mt-6 flex flex-col gap-4">
      <h3 className="flex items-center gap-2 font-semibold">
        <BellRing className="size-5 text-flame-400" /> {t("Eslatmalar")}
      </h3>
      <div>
        <Label>{t("Vazifadan oldin eslatish")}</Label>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {LEADS.map((minutes) => (
            <button
              key={minutes}
              onClick={() => setLead(minutes)}
              aria-pressed={lead === minutes}
              className={`rounded-xl px-3 py-1.5 text-sm font-semibold transition ${lead === minutes ? "bg-flame text-white" : "bg-white/5 text-mist hover:text-white"}`}
            >
              {minutes === 0 ? t("O'chiq") : t("{m} daq", { m: minutes })}
            </button>
          ))}
        </div>
      </div>
      <label className="flex items-start gap-3">
        <input type="checkbox" checked={quiet} onChange={(e) => setQuiet(e.target.checked)} className="mt-1 size-4 accent-flame-500" />
        <span className="text-sm">
          <b>{t("Tinch soatlar")}</b>
          <span className="block text-xs text-mist">{t("Bu vaqtda Telegram va telefon xabar yubormaydi — hammasi ilovada kutib turadi.")}</span>
        </span>
      </label>
      {quiet && (
        <div className="grid grid-cols-2 gap-3">
          <label>
            <Label>{t("Boshlanishi")}</Label>
            <Input type="time" value={from} onChange={(e) => setFrom(e.target.value)} className="[color-scheme:dark]" />
          </label>
          <label>
            <Label>{t("Tugashi")}</Label>
            <Input type="time" value={to} onChange={(e) => setTo(e.target.value)} className="[color-scheme:dark]" />
          </label>
        </div>
      )}
      <label className="flex items-start gap-3">
        <input type="checkbox" checked={friends} onChange={(e) => setFriends(e.target.checked)} className="mt-1 size-4 accent-flame-500" />
        <span className="text-sm">
          <b>{t("Do'stlar yangiliklari")}</b>
          <span className="block text-xs text-mist">{t("Do'stingiz bugun bajarganda yoki guruhga qo'shilganda xabar berish.")}</span>
        </span>
      </label>
      <Button loading={saving} onClick={save} disabled={quiet && from === to}>
        {t("Saqlash")}
      </Button>
    </Card>
  );
}
