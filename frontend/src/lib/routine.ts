import type { BusyBlock } from "./types";

// Mirrors backend planning/domain/routine.py so the wizard can show free time as you type.
const WAKE_UP_MINUTES = 15;
const MIN_SLOT_MINUTES = 15;

export const toMinutes = (clock: string) => {
  const [h, m] = clock.split(":").map(Number);
  return h * 60 + m;
};

/** Sleeping after midnight (wake 07:00, sleep 00:30) still ends the planning day at 24:00. */
export const dayEnd = (wake: string, sleep: string) => (sleep <= wake ? 24 * 60 : toMinutes(sleep));

/** At least 6 waking hours, counting past midnight. */
export const awakeLongEnough = (wake: string, sleep: string) => (toMinutes(sleep) - toMinutes(wake) + 24 * 60) % (24 * 60) >= 6 * 60;

export function freeMinutes(wake: string, sleep: string, busy: BusyBlock[], weekday: number): number {
  let cursor = toMinutes(wake) + WAKE_UP_MINUTES;
  const end = dayEnd(wake, sleep);
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

export type FrameLike = { wake: string; sleep: string; busy: BusyBlock[] };

const clock = (total: number) => `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;

/** Why a task at `at` does not fit the day frame, as [dictionary key, values] — or null.
 * Mirrors check_clashes on the server so the user sees the reason while typing. */
export function timeProblem(
  frame: FrameLike | null | undefined,
  at: string,
  minutes: number,
  weekdays: number[],
): [string, Record<string, string>] | null {
  if (!frame || !at) return null;
  const start = toMinutes(at);
  const end = start + minutes;
  if (start < toMinutes(frame.wake)) return ["Uyg'onish {wake} — undan keyin boshlang", { wake: frame.wake }];
  const last = dayEnd(frame.wake, frame.sleep);
  if (end > last) {
    return ["Uxlash {sleep} — ko'pi bilan {latest} da boshlang", { sleep: frame.sleep, latest: clock(Math.max(0, last - minutes)) }];
  }
  const busy = frame.busy.find((b) => b.weekdays.some((d) => weekdays.includes(d)) && start < toMinutes(b.end) && toMinutes(b.start) < end);
  if (busy) return ["«{label}» bilan ustma-ust ({from}–{to})", { label: busy.label, from: busy.start, to: busy.end }];
  return null;
}
