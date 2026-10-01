"use client";

import { useState, useSyncExternalStore } from "react";

import { Button, Modal } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

const SEEN_KEY = "pit.welcome.v1";

const STEPS = [
  {
    icon: "🎯",
    title: "1. Maqsad tanlang",
    body: "«Yangi maqsad» tugmasi: AI sizga reja tuzadi yoki tayyor challenge tanlaysiz. Har kuni nima qilish aniq yoziladi.",
  },
  {
    icon: "📸",
    title: "2. Har kuni bajaring va isbot yuboring",
    body: "«Bugun» sahifasida kunlik vazifalar soatma-soat turadi. Bajargach, rasm yoki qisqa matn yuboring — AI tekshiradi.",
  },
  {
    icon: "🔥",
    title: "3. Streak o'sadi",
    body: "Streak — ketma-ket bajarilgan kunlar. Bir kun o'tkazsangiz, freeze (zaxira kun) uni saqlab qoladi. 7 kun ketma-ket bajarsangiz, freeze qaytadi.",
  },
];

const noUpdates = () => () => {};
const readSeen = () => {
  try {
    return localStorage.getItem(SEEN_KEY) === "1";
  } catch {
    return true; // storage blocked: never nag
  }
};

/** How PIT works, in three steps — once, the first time someone opens the app. */
export function Welcome() {
  const { t } = useI18n();
  const seen = useSyncExternalStore(noUpdates, readSeen, () => true);
  const [closed, setClosed] = useState(false);
  const [step, setStep] = useState(0);

  function close() {
    try {
      localStorage.setItem(SEEN_KEY, "1");
    } catch {}
    setClosed(true);
  }

  const current = STEPS[step];
  const last = step === STEPS.length - 1;
  return (
    <Modal open={!seen && !closed} onClose={close} title={t("PIT qanday ishlaydi?")}>
      <div className="flex flex-col items-center gap-3 py-2 text-center">
        <span className="text-5xl">{current.icon}</span>
        <p className="font-display text-lg font-semibold">{t(current.title)}</p>
        <p className="text-mist">{t(current.body)}</p>
      </div>
      <div className="mt-4 flex justify-center gap-1.5" aria-hidden>
        {STEPS.map((_, index) => (
          <span key={index} className={`h-1.5 w-6 rounded-full ${index === step ? "bg-flame-400" : "bg-white/10"}`} />
        ))}
      </div>
      <div className="mt-6 flex gap-2">
        <Button variant="ghost" onClick={close}>
          {t("O'tkazib yuborish")}
        </Button>
        <Button className="flex-1" onClick={() => (last ? close() : setStep((s) => s + 1))}>
          {last ? t("Boshladik! 🚀") : t("Keyingisi")}
        </Button>
      </div>
    </Modal>
  );
}
