"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import useSWR from "swr";

import { Card } from "@/components/ui";
import type { Badge } from "@/lib/types";

/** Earned badges shine; locked ones show what it takes — a goal, not a wall. */
export function Badges() {
  const { data } = useSWR<Badge[]>("/me/badges");
  if (!data) return null;
  const earned = data.filter((badge) => badge.earned).length;

  return (
    <Card className="mt-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Nishonlar</h3>
        <span className="text-sm text-mist">
          {earned}/{data.length}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
        {data.map((badge, index) => (
          <motion.div
            key={badge.key}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.03 }}
            title={badge.earned ? badge.title : badge.hint}
            className={clsx(
              "flex flex-col items-center gap-1.5 rounded-2xl border p-3 text-center",
              badge.earned ? "border-flame-500/30 bg-flame-500/10" : "border-white/5 bg-white/[0.02]",
            )}
          >
            <span className={clsx("text-3xl", !badge.earned && "opacity-30 grayscale")}>{badge.emoji}</span>
            <span className={clsx("text-xs font-semibold", !badge.earned && "text-mist")}>{badge.title}</span>
            {!badge.earned && <span className="text-[11px] leading-tight text-mist/80">{badge.hint}</span>}
          </motion.div>
        ))}
      </div>
    </Card>
  );
}
