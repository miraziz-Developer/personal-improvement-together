"use client";

import { Bell, BellOff, Download, Smartphone } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

import { useToast } from "@/components/toast";
import { Button, Card } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useFeatures } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

type InstallPrompt = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };

const noSubscription = () => () => {};
const pushSupported = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
const isInstalled = () => window.matchMedia("(display-mode: standalone)").matches;

function base64UrlToBytes(value: string): Uint8Array<ArrayBuffer> {
  const padded = (value + "=".repeat((4 - (value.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(padded);
  const bytes = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

/** Profile: install the site as an app and get the coach's messages as phone notifications. */
export function AppInstall() {
  const { pushPublicKey } = useFeatures();
  const toast = useToast();
  const { t, tx } = useI18n();
  const supported = useSyncExternalStore(noSubscription, pushSupported, () => false);
  const ios = useSyncExternalStore(noSubscription, isIos, () => false);
  const installed = useSyncExternalStore(noSubscription, isInstalled, () => false);
  const [subscribed, setSubscribed] = useState<boolean | null>(null);
  const [installPrompt, setInstallPrompt] = useState<InstallPrompt | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!supported) return;
    navigator.serviceWorker.ready
      .then((registration) => registration.pushManager.getSubscription())
      .then((subscription) => setSubscribed(subscription !== null))
      .catch(() => setSubscribed(false));
  }, [supported]);

  useEffect(() => {
    const keep = (event: Event) => {
      event.preventDefault(); // show our own button instead of the browser's mini-bar
      setInstallPrompt(event as InstallPrompt);
    };
    window.addEventListener("beforeinstallprompt", keep);
    return () => window.removeEventListener("beforeinstallprompt", keep);
  }, []);

  async function enable() {
    if (!pushPublicKey) return;
    setBusy(true);
    try {
      if ((await Notification.requestPermission()) !== "granted") {
        toast("info", t("Ruxsat berilmadi"), t("Brauzer sozlamalarida bu sayt uchun bildirishnomalarni yoqing."));
        return;
      }
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: base64UrlToBytes(pushPublicKey),
      });
      await api("/me/push", { method: "POST", json: subscription.toJSON() });
      setSubscribed(true);
      toast("success", t("Bildirishnomalar yoqildi 🔔"), t("Murabbiy xabarlari endi telefoningizga keladi."));
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    setBusy(true);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await api("/me/push", { method: "DELETE", json: { endpoint: subscription.endpoint } });
        await subscription.unsubscribe();
      }
      setSubscribed(false);
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function install() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  }

  const canPush = Boolean(pushPublicKey) && supported;
  if (!canPush && !installPrompt && !(ios && !installed)) return null;

  return (
    <Card className="mt-6">
      <h3 className="flex items-center gap-2 font-semibold">
        <Smartphone className="size-4" /> {t("Ilova va bildirishnomalar")}
      </h3>
      <div className="mt-4 flex flex-col gap-3">
        {installPrompt && (
          <Button variant="secondary" onClick={install}>
            <Download className="size-4" /> {t("Telefonga ilova sifatida o'rnatish")}
          </Button>
        )}
        {ios && !installed && (
          <p className="rounded-2xl bg-white/[0.03] p-3 text-sm text-mist">
            {tx("iPhone'da: Safari'da {steps}. Shundan keyin bildirishnomalarni ham yoqasiz.", {
              steps: <b className="text-white">{t("Ulashish → Bosh ekranga qo'shish")}</b>,
            })}
          </p>
        )}
        {canPush &&
          (subscribed ? (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="flex items-center gap-2 text-sm text-mint">
                <Bell className="size-4" /> {t("Bu qurilmada bildirishnomalar yoqilgan")}
              </p>
              <Button variant="ghost" size="sm" loading={busy} onClick={disable}>
                <BellOff className="size-4" /> {t("O'chirish")}
              </Button>
            </div>
          ) : (
            <Button loading={busy || subscribed === null} onClick={enable}>
              <Bell className="size-4" /> {t("Bildirishnomalarni yoqish")}
            </Button>
          ))}
      </div>
    </Card>
  );
}
