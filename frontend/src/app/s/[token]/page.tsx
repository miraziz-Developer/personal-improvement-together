import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CATEGORY_EMOJI, fetchShared, headline } from "@/lib/share";

type Props = { params: Promise<{ token: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const shared = await fetchShared((await params).token);
  if (!shared) return { title: "PIT" };
  const { big, small } = headline(shared);
  const title = `${shared.username}: ${big} ${small.replace(/[🔥🏆]/gu, "").trim()} — ${shared.title}`;
  const description = "PIT — maqsadlaringizni har kungi odatga aylantiradigan murabbiy. Men bilan birga boshla!";
  return { title, description, openGraph: { title, description }, twitter: { card: "summary_large_image", title, description } };
}

/** What a friend sees when the link is opened: the result, and a way to start too. */
export default async function SharedPage({ params }: Props) {
  const { token } = await params;
  const shared = await fetchShared(token);
  if (!shared) notFound();
  const { big, small } = headline(shared);
  const progress = shared.total_days ? Math.min(shared.days_completed / shared.total_days, 1) : 0;
  return (
    <main className="grid min-h-dvh place-items-center px-5 py-10">
      <div className="glass w-full max-w-md rounded-3xl p-6 text-center">
        <p className="text-sm text-mist">@{shared.username}</p>
        <p className="mt-3 font-display text-6xl font-bold text-flame-400">{big}</p>
        <p className="mt-1 text-lg font-semibold">{small}</p>
        <p className="mt-4 text-lg">
          {CATEGORY_EMOJI[shared.category] ?? "🎯"} {shared.title}
        </p>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
          <div className="bg-flame h-full rounded-full" style={{ width: `${progress * 100}%` }} />
        </div>
        <p className="mt-2 text-sm text-mist">
          {shared.days_completed}/{shared.total_days} kun · eng uzun streak {shared.best_streak}
        </p>
        <Link href="/register" className="bg-flame glow-flame mt-6 block rounded-2xl py-3 font-semibold text-white">
          Men ham boshlayman 🚀
        </Link>
        <p className="mt-3 text-xs text-mist">PIT — har kuni kichik qadam, katta natija. Bepul.</p>
      </div>
    </main>
  );
}
