import Link from "next/link";

import { Logo } from "@/components/AppShell";

export default function LegalLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="mx-auto max-w-3xl px-5 py-8">
      <header className="flex items-center justify-between">
        <Logo />
        <nav className="flex gap-4 text-sm text-mist">
          <Link href="/terms" className="hover:text-white">
            Shartlar
          </Link>
          <Link href="/privacy" className="hover:text-white">
            Maxfiylik
          </Link>
        </nav>
      </header>
      <article className="glass mt-8 rounded-3xl p-6 leading-relaxed text-white/85 sm:p-10 [&_h1]:font-display [&_h1]:text-3xl [&_h1]:font-bold [&_h1]:text-white [&_h2]:mt-8 [&_h2]:font-display [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-white [&_li]:mt-1.5 [&_p]:mt-3 [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5">
        {children}
      </article>
      <p className="mt-6 text-center text-sm text-mist">
        Savollar va so'rovlar: <a href="mailto:support@pit.uz" className="text-flame-400 hover:text-flame-300">support@pit.uz</a>
      </p>
    </div>
  );
}
