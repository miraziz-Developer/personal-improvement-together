"use client";

import { Check, Copy, Download, Send, Share2 } from "lucide-react";
import { useState } from "react";

import { useToast } from "@/components/toast";
import { Button, Modal } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** Share a run: a link with a picture card (Telegram shows it), a story image, the phone's menu. */
export function ShareButton({ participationId }: { participationId: string }) {
  const { t } = useI18n();
  const toast = useToast();
  const [link, setLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function open() {
    setLoading(true);
    try {
      const { token } = await api<{ token: string }>(`/me/participations/${participationId}/share`, { method: "POST" });
      setLink(`${window.location.origin}/s/${token}`);
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  const text = t("Men PIT'da maqsadim sari har kuni harakat qilyapman 🔥 Qo'shil!");

  async function copy() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast("error", t("Nusxalab bo'lmadi — havolani qo'lda belgilang."));
    }
  }

  async function native() {
    if (!link) return;
    try {
      await navigator.share({ url: link, text });
    } catch {
      // closed the menu: nothing to do
    }
  }

  return (
    <>
      <Button size="sm" variant="secondary" loading={loading} onClick={open}>
        <Share2 className="size-4" /> {t("Ulashish")}
      </Button>
      <Modal open={link !== null} onClose={() => setLink(null)} title={t("Natijangizni ulashing")}>
        {link && (
          <div className="flex flex-col gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`${link}/opengraph-image`} alt={t("Ulashish kartasi")} className="w-full rounded-2xl border border-white/10" />
            <Button href={`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`} external variant="sky">
              <Send className="size-4" /> {t("Telegram'da ulashish")}
            </Button>
            <Button href={`${link}/story`} external variant="secondary">
              <Download className="size-4" /> {t("Story uchun rasm (Instagram, Telegram)")}
            </Button>
            <div className="flex gap-2">
              <Button variant="ghost" className="flex-1" onClick={copy}>
                {copied ? <Check className="size-4 text-mint" /> : <Copy className="size-4" />} {t("Havolani nusxalash")}
              </Button>
              {typeof navigator !== "undefined" && "share" in navigator && (
                <Button variant="ghost" className="flex-1" onClick={native}>
                  <Share2 className="size-4" /> {t("Boshqa ilovalar")}
                </Button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
