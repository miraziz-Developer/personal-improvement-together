"use client";

import { Logo } from "@/components/AppShell";
import { LanguageSwitch } from "@/components/LanguageSwitch";
import { useI18n } from "@/lib/i18n";

const PROMISES = [
  { emoji: "🎯", text: "Maqsadingizni ayting — AI sizga haftalik reja tuzadi" },
  { emoji: "📸", text: "Har kuni isbot yuboring, streak'ingiz o'sadi" },
  { emoji: "🤝", text: "Murabbiy qiyin kunlarda ham yoningizda" },
  { emoji: "🏆", text: "Tengdoshlaringiz va hududingiz bilan bellashing" },
];

export default function AuthLayout({ children }: LayoutProps<"/">) {
  const { t } = useI18n();
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <section className="relative hidden overflow-hidden border-r border-white/5 p-12 lg:flex lg:flex-col">
        <Logo />
        <div className="my-auto max-w-md">
          <h2 className="font-display text-4xl leading-tight font-bold">
            {t("Bugun boshlagan odat —")} <span className="text-flame">{t("ertangi sizni")}</span> {t("quradi.")}
          </h2>
          <ul className="mt-10 flex flex-col gap-4">
            {PROMISES.map((p) => (
              <li key={p.text} className="glass flex items-center gap-4 rounded-2xl p-4">
                <span className="text-2xl">{p.emoji}</span>
                <span className="text-white/85">{t(p.text)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-flame absolute -bottom-32 -left-32 size-96 rounded-full opacity-20 blur-3xl" />
      </section>
      <section className="flex items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <div className="mb-10 flex items-center justify-between lg:mb-6 lg:justify-end">
            <Logo className="lg:hidden" />
            <LanguageSwitch />
          </div>
          {children}
        </div>
      </section>
    </div>
  );
}
