"use client";

import clsx from "clsx";
import { Flame, Trophy } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { Card, Skeleton } from "@/components/ui";
import type { ChallengeBoard as Board } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

const MEDALS = ["🥇", "🥈", "🥉"];
const SHOWN = 10;

type Entry = Board["entries"][number];

/** Who joined a catalog challenge and who leads it. Personal plans have no board: renders nothing. */
export function ChallengeBoard({ challengeId }: { challengeId: string }) {
  const { t } = useI18n();
  const [all, setAll] = useState(false);
  const { data, error } = useSWR<Board>(`/challenges/${challengeId}/leaderboard`, { refreshInterval: 60_000 });

  if (error) return null;
  if (!data) return <Skeleton className="h-48" />;

  const rows = all ? data.entries : data.entries.slice(0, SHOWN);
  const meBelow = rows.some((e) => e.is_me) ? undefined : data.entries.find((e) => e.is_me);

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
            <Trophy className="size-5 text-amberish" /> {t("Challenge reytingi")}
          </h2>
          <p className="mt-1 text-sm text-mist">{t("{n} kishi qo'shilgan", { n: data.size })}</p>
        </div>
        {data.me && (
          <div className="shrink-0 rounded-2xl bg-flame-500/10 px-3 py-2 text-center">
            <p className="text-xs text-mist">{t("Sizning o'rningiz")}</p>
            <p className="font-display text-xl font-bold text-flame">#{data.me.rank}</p>
          </div>
        )}
      </div>

      {data.size === 0 ? (
        <p className="mt-4 rounded-2xl bg-white/[0.03] p-4 text-center text-sm text-mist">{t("Hali hech kim yo'q — birinchi bo'ling! 🏁")}</p>
      ) : (
        <ol className="mt-4 flex flex-col gap-1">
          {rows.map((e) => (
            <Row key={e.user_id} entry={e} />
          ))}
          {meBelow && (
            <>
              <li className="px-4 text-mist" aria-hidden>
                ⋯
              </li>
              <Row entry={meBelow} />
            </>
          )}
        </ol>
      )}

      {data.entries.length > SHOWN && (
        <button onClick={() => setAll((v) => !v)} className="mt-3 w-full rounded-xl py-2 text-sm font-semibold text-mist transition hover:bg-white/5 hover:text-white">
          {all ? t("Kamroq ko'rsatish") : t("Hammasini ko'rish ({n})", { n: data.entries.length })}
        </button>
      )}
    </Card>
  );
}

function Row({ entry: e }: { entry: Entry }) {
  const { t } = useI18n();
  return (
    <li className={clsx("flex items-center gap-3 rounded-2xl px-3 py-2.5", e.is_me ? "bg-flame-500/10" : "bg-white/[0.02]")}>
      <span className="w-8 shrink-0 text-center font-display font-bold text-mist">{e.rank <= 3 ? MEDALS[e.rank - 1] : e.rank}</span>
      <span className="min-w-0 flex-1 truncate font-medium">
        {e.username} {e.is_me && <span className="text-flame-400">{t("(siz)")}</span>}
      </span>
      {e.streak > 0 && (
        <span className="flex shrink-0 items-center gap-0.5 text-sm text-flame-400" title={t("Joriy streak")}>
          <Flame className="size-4" />
          {e.streak}
        </span>
      )}
      <span className="w-14 shrink-0 text-right font-semibold tabular-nums">{e.points}</span>
    </li>
  );
}
