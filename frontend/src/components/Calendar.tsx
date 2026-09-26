import clsx from "clsx";

import { DAY_STATUS, WEEKDAYS_SHORT } from "@/lib/format";
import type { DayStatus } from "@/lib/types";

function isoDay(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function Calendar({
  start,
  end,
  days,
  today,
}: {
  start: string;
  end: string;
  days: { date: string; status: DayStatus }[];
  today: string;
}) {
  const byDate = new Map(days.map((d) => [d.date, d.status]));
  const first = new Date(`${start}T00:00:00`);
  const last = new Date(`${end}T00:00:00`);
  const offset = (first.getDay() + 6) % 7; // Monday first
  const cells: (Date | null)[] = Array.from({ length: offset }, () => null);
  for (let d = new Date(first); d <= last; d.setDate(d.getDate() + 1)) cells.push(new Date(d));

  return (
    <div>
      <div className="grid grid-cols-7 gap-1.5 text-center text-[11px] text-mist">
        {WEEKDAYS_SHORT.map((w) => (
          <span key={w}>{w}</span>
        ))}
      </div>
      <div className="mt-2 grid grid-cols-7 gap-1.5">
        {cells.map((date, i) => {
          if (!date) return <span key={`gap-${i}`} />;
          const key = isoDay(date);
          const status = byDate.get(key);
          return (
            <div
              key={key}
              title={status ? DAY_STATUS[status].label : "Dam olish kuni"}
              className={clsx(
                "grid aspect-square place-items-center rounded-lg text-[11px] font-semibold",
                status ? DAY_STATUS[status].cell : "bg-transparent text-white/20",
                key === today && "ring-2 ring-flame-400 ring-offset-2 ring-offset-ink-900",
              )}
            >
              {date.getDate()}
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex flex-wrap gap-3 text-xs text-mist">
        {(["done", "frozen", "awaiting_review", "missed", "pending"] as DayStatus[]).map((s) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className={clsx("size-2.5 rounded-full", DAY_STATUS[s].dot)} /> {DAY_STATUS[s].label}
          </span>
        ))}
      </div>
    </div>
  );
}
