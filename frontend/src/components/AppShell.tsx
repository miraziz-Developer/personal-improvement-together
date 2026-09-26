"use client";

import clsx from "clsx";
import { Bell, Compass, Flame, Home, LogOut, Plus, Shield, Trophy, User, Wallet } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { LanguageSwitch } from "@/components/LanguageSwitch";
import { Spinner } from "@/components/ui";
import { useAuth, useFeatures } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

const NAV = [
  { href: "/dashboard", label: "Bosh sahifa", short: "Bosh", icon: Home },
  { href: "/challenges", label: "Challenge'lar", short: "Challenge", icon: Compass },
  { href: "/leaderboard", label: "Reyting", short: "Reyting", icon: Trophy },
  { href: "/wallet", label: "Hamyon", short: "Hamyon", icon: Wallet },
  { href: "/profile", label: "Profil", short: "Profil", icon: User },
];

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={clsx("flex items-center gap-2.5", className)}>
      <span className="bg-flame glow-flame grid size-9 place-items-center rounded-xl">
        <Flame className="size-5 text-white" fill="currentColor" />
      </span>
      <span className="font-display text-xl font-bold tracking-tight">PIT</span>
    </Link>
  );
}

function Bellbutton({ unread }: { unread: number }) {
  const { t } = useI18n();
  return (
    <Link href="/notifications" className="relative rounded-xl p-2.5 text-mist transition hover:bg-white/5 hover:text-white" aria-label={t("Xabarlar")}>
      <Bell className="size-5" />
      {unread > 0 && (
        <span className="bg-flame absolute -top-0.5 -right-0.5 grid min-w-5 place-items-center rounded-full px-1 text-[11px] font-bold text-white">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { ready, token, me, signOut } = useAuth();
  const { stakesEnabled } = useFeatures();
  const { t } = useI18n();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (ready && !token) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [ready, token, pathname, router]);

  if (!ready || !token) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <Spinner className="size-8" />
      </div>
    );
  }

  const base = stakesEnabled ? NAV : NAV.filter((item) => item.href !== "/wallet");
  const nav = me && me.role !== "user" ? [...base, { href: "/admin", label: "Moderator", short: "Moderator", icon: Shield }] : base;
  const active = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <div className="min-h-dvh lg:flex">
      <aside className="sticky top-0 hidden h-dvh w-68 shrink-0 flex-col border-r border-white/5 bg-ink-950/40 p-5 lg:flex">
        <Logo />
        <Link
          href="/onboarding"
          className="bg-flame glow-flame mt-8 flex items-center justify-center gap-2 rounded-2xl py-3 font-semibold text-white transition hover:brightness-110"
        >
          <Plus className="size-5" /> {t("Yangi maqsad")}
        </Link>
        <nav className="mt-6 flex flex-col gap-1">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-2xl px-4 py-3 font-medium transition",
                active(href) ? "bg-white/[0.08] text-white" : "text-mist hover:bg-white/[0.04] hover:text-white",
              )}
            >
              <Icon className={clsx("size-5", active(href) && "text-flame-400")} />
              {t(label)}
            </Link>
          ))}
        </nav>
        <div className="mt-auto">
          {me && (
            <div className="glass flex items-center gap-3 rounded-2xl p-3">
              <div className="bg-flame grid size-10 place-items-center rounded-xl font-display font-bold uppercase">
                {me.username[0]}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{me.username}</p>
                <p className="text-xs text-mist">{t("{n} ball", { n: me.points })}</p>
              </div>
              <button onClick={signOut} className="rounded-xl p-2 text-mist hover:bg-white/5 hover:text-white" aria-label={t("Chiqish")}>
                <LogOut className="size-4" />
              </button>
            </div>
          )}
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/5 bg-ink-950/70 px-4 py-3 backdrop-blur-xl sm:px-8">
          <Logo className="lg:invisible" />
          <div className="flex items-center gap-1">
            <LanguageSwitch className="mr-1" />
            <Bellbutton unread={me?.unread_notifications ?? 0} />
            <Link href="/onboarding" className="rounded-xl p-2.5 text-mist hover:bg-white/5 hover:text-white lg:hidden" aria-label={t("Yangi maqsad")}>
              <Plus className="size-5" />
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 pt-6 pb-32 sm:px-8 lg:pb-12">{children}</main>
      </div>

      <nav
        style={{ gridTemplateColumns: `repeat(${base.length}, minmax(0, 1fr))` }}
        className="fixed inset-x-3 bottom-3 z-40 grid rounded-3xl border border-white/10 bg-ink-800/85 p-1.5 shadow-2xl backdrop-blur-xl lg:hidden">
        {base.map(({ href, short, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex flex-col items-center gap-1 rounded-2xl py-2 text-[11px] font-medium transition",
              active(href) ? "bg-white/10 text-white" : "text-mist",
            )}
          >
            <Icon className={clsx("size-5", active(href) && "text-flame-400")} />
            {t(short)}
          </Link>
        ))}
      </nav>
    </div>
  );
}
