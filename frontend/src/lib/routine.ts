import type { BusyBlock } from "./types";

// Mirrors backend planning/domain/routine.py so the wizard can show free time as you type.
const WAKE_UP_MINUTES = 15;
const MIN_SLOT_MINUTES = 15;

export const toMinutes = (clock: string) => {
  const [h, m] = clock.split(":").map(Number);
  return h * 60 + m;
};

export function freeMinutes(wake: string, sleep: string, busy: BusyBlock[], weekday: number): number {
  let cursor = toMinutes(wake) + WAKE_UP_MINUTES;
  const end = toMinutes(sleep);
  let free = 0;
  const blocks = busy.filter((b) => b.weekdays.includes(weekday)).sort((a, b) => toMinutes(a.start) - toMinutes(b.start));
  for (const block of blocks) {
    const start = toMinutes(block.start);
    if (start - cursor >= MIN_SLOT_MINUTES) free += Math.min(start, end) - cursor;
    cursor = Math.max(cursor, toMinutes(block.end));
  }
  if (end - cursor >= MIN_SLOT_MINUTES) free += end - cursor;
  return Math.max(0, free);
}
