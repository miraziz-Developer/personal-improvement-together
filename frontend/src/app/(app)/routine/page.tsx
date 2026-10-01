"use client";

import { BookOpen, CalendarClock, Check, Clock, Flag, Pencil, Plus, Sparkles } from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import useSWR from "swr";

import { AddToRoutine } from "@/components/AddToRoutine";
import { DayFrameEditor, type DayFrameValue, frameIsValid } from "@/components/DayFrameEditor";
import { ProofTask } from "@/components/ProofTask";
import { useToast } from "@/components/toast";
import { Timeline, type TimelineEntry } from "@/components/Timeline";
import { CoachFeed } from "@/components/coach";
import { TelegramNudge } from "@/components/Telegram";
import { Welcome } from "@/components/Welcome";
import { Button, Card, EmptyState, PageHeader, Skeleton, StreakFlame } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, errorMessage } from "@/lib/api";
import { greeting, shortDate, WEEKDAYS_SHORT } from "@/lib/format";
import { type FrameLike, timeProblem } from "@/lib/routine";
import { useI18n } from "@/lib/i18n";
import type { Routine, RoutineItem } from "@/lib/types";

const everyMinute = (callback: () => void) => {
  const timer = setInterval(callback, 60_000);
  return () => clearInterval(timer);
};
const noUpdates = () => () => {};
const clockNow = () => new Date().toTimeString().slice(0, 5);

/** Moves a task on the timeline. The time holds on every day the task happens. */
function TimeField({ item, onSaved, frame }: { item: RoutineItem; onSaved: () => void; frame: FrameLike | null }) {
  const { t } = useI18n();
  const toast = useToast();
  const [value, setValue] = useState(item.task?.at ?? "");
  const [saving, setSaving] = useState(false);
  const changed = value !== (item.task?.at ?? "");
  const problem = timeProblem(frame, value, item.task?.minutes ?? 0, [(new Date().getDay() + 6) % 7]);

  async function save() {
    if (!item.task || !item.participation_id) return;
    setSaving(true);
    try {
      await api(`/me/participations/${item.participation_id}/times`, { method: "PUT", json: { times: { [item.task.key]: value || null } } });
      toast("success", value ? t("Vaqt saqlandi: {time}", { time: value }) : t("Vaqt olib tashlandi"));
      onSaved();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 px-1">
      <label className="flex items-center gap-1.5 rounded-xl bg-white/5 px-2 py-1 text-xs text-mist focus-within:text-white">
        <Clock className="size-3.5" />
        <input
          type="time"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="bg-transparent tabular-nums outline-none [color-scheme:dark]"
          aria-label={t("Boshlanish vaqti")}
        />
      </label>
      {problem && <span className="text-xs text-danger">{t(problem[0], problem[1])}</span>}
      {changed && !problem && (
        <button onClick={save} disabled={saving} className="flex items-center gap-1 rounded-xl bg-flame-500/20 px-2.5 py-1 text-xs font-semibold text-flame-200 hover:bg-flame-500/30 disabled:opacity-50">
          <Check className="size-3.5" /> {t("Saqlash")}
        </button>
      )}
    </div>
  );
}

function TaskEntry({
  item,
  onSubmitted,
  editing,
  showLesson,
  frame,
  preview,
}: {
  item: RoutineItem;
  onSubmitted: () => void;
  editing: boolean;
  showLesson: boolean;
  frame: FrameLike | null;
  preview: boolean; // another day than today: nothing to prove yet
}) {
  const { t } = useI18n();
  if (!item.task || !item.participation_id) return null;
  return (
    <div className="flex flex-col gap-1.5">
      <p className="px-1 text-xs text-mist">
        {item.challenge_title}
        {item.end && ` · ${t("{time} gacha", { time: item.end })}`}
      </p>
      {editing && <TimeField key={item.task.at ?? ""} item={item} onSaved={onSubmitted} frame={frame} />}
      {showLesson && item.lesson && (
        <p className="flex items-center gap-1.5 px-1 text-xs text-iris">
          <BookOpen className="size-3.5" /> {item.lesson}
        </p>
      )}
      {preview ? (
        <div className="flex flex-wrap items-center gap-2 rounded-3xl border border-white/10 bg-white/[0.02] p-4">
          {item.task.at && <span className="rounded-lg bg-white/10 px-1.5 py-0.5 text-xs font-semibold tabular-nums">{item.task.at}</span>}
          <p className="font-semibold">{item.task.title}</p>
          <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-mist">{t("{m} daq", { m: item.task.minutes })}</span>
          {!item.task.required && <span className="text-xs text-mist">{t("qo'shimcha")}</span>}
        </div>
      ) : (
        <ProofTask participationId={item.participation_id} task={item.task} onSubmitted={onSubmitted} />
      )}
    </div>
  );
}

const AHEAD_DAYS = 7;

function isoDay(offset: number): string {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Today, tomorrow and the rest of the week — to see what is coming. */
function DayStrip({ offset, onChange }: { offset: number; onChange: (offset: number) => void }) {
  const { t } = useI18n();
  return (
    <div className="mb-4 flex gap-1.5 overflow-x-auto pb-1">
      {Array.from({ length: AHEAD_DAYS }, (_, i) => {
        const day = isoDay(i);
        const weekday = (new Date(`${day}T00:00:00`).getDay() + 6) % 7;
        const label = i === 0 ? t("Bugun") : i === 1 ? t("Ertaga") : t(WEEKDAYS_SHORT[weekday]);
        return (
          <button
            key={day}
            onClick={() => onChange(i)}
            aria-pressed={offset === i}
            className={`flex shrink-0 flex-col items-center rounded-2xl px-3.5 py-2 text-sm transition ${offset === i ? "bg-flame text-white" : "bg-white/5 text-mist hover:text-white"}`}
          >
            <span className="font-semibold">{label}</span>
            <span className="text-xs opacity-80">{shortDate(day)}</span>
          </button>
        );
      })}
    </div>
  );
}

/** Wake/sleep and commitments of the routine being lived. */
function FrameCard({ frame, onSaved }: { frame: DayFrameValue; onSaved: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const [value, setValue] = useState(frame);
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await api("/me/life-plan/frame", { method: "PUT", json: value });
      toast("success", t("Kun tartibi yangilandi"));
      onSaved();
    } catch (error) {
      toast("error", errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="mb-4 flex flex-col gap-4">
      <h2 className="font-display text-lg font-semibold">{t("Kuningiz")}</h2>
      <DayFrameEditor value={value} onChange={setValue} />
      <Button loading={saving} disabled={!frameIsValid(value)} onClick={save}>
        {t("Saqlash")}
      </Button>
    </Card>
  );
}

export default function RoutinePage() {
  const { t } = useI18n();
  const { me } = useAuth();
  const [offset, setOffset] = useState(0);
  const { data, mutate } = useSWR<Routine>(offset ? `/me/routine?day=${isoDay(offset)}` : "/me/routine", {
    refreshInterval: 60_000,
    keepPreviousData: true, // switching days keeps the page in place while the next loads
  });
  const now = useSyncExternalStore(everyMinute, clockNow, () => "");
  const [editing, setEditing] = useState(false);
  const [adding, setAdding] = useState(false);
  // "New goal → ready challenge" lands here with ?add=1: the picker opens straight away.
  const asked = useSyncExternalStore(noUpdates, () => window.location.search.includes("add=1"), () => false);
  const [pickerClosed, setPickerClosed] = useState(false);

  if (!data) return <Skeleton className="h-96" />;

  const refresh = () => mutate();
  const lessonShown = new Set<string>();
  const entries: TimelineEntry[] = data.items.map((item) => {
    // A challenge's lesson is shown once, at its first task of the day.
    const showLesson = Boolean(item.participation_id && !lessonShown.has(item.participation_id));
    if (item.participation_id) lessonShown.add(item.participation_id);
    return {
      kind: item.kind,
      start: item.start,
      end: item.end,
      title: item.title,
      category: item.category,
      children: item.kind === "task" ? <TaskEntry item={item} onSubmitted={refresh} editing={editing} showLesson={showLesson} frame={data.frame} preview={!data.is_today} /> : undefined,
    };
  });
  const nothing = data.items.every((i) => i.kind !== "task") && data.untimed.length === 0;
  const tasksToday = [...data.items, ...data.untimed].filter((i) => i.kind === "task" && i.task?.required);
  const doneToday = tasksToday.filter((i) => i.task?.proof_status === "approved").length;

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title={me ? greeting(me.username) : t("Bugun")}
        subtitle={data.is_today ? t("Bugun, {date}", { date: shortDate(data.date) }) : shortDate(data.date)}
        action={
          !nothing || data.has_life_plan ? (
            <Button size="sm" variant={editing ? "primary" : "secondary"} onClick={() => setEditing((v) => !v)}>
              {editing ? <Check className="size-4" /> : <Pencil className="size-4" />} {editing ? t("Tayyor") : t("Tahrirlash")}
            </Button>
          ) : undefined
        }
      />

      {data.is_today && !nothing && (
        <div className="mb-4 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-2xl bg-white/[0.04] px-2 py-3">
            <p className="font-display text-xl font-bold tabular-nums">
              {doneToday}/{tasksToday.length}
            </p>
            <p className="text-xs text-mist">{t("bugun bajarildi")}</p>
          </div>
          <div className="rounded-2xl bg-white/[0.04] px-2 py-3" title={t("Streak — ketma-ket bajarilgan kunlar. Bir kun o'tkazsangiz, freeze uni saqlab qoladi.")}>
            <div className="flex justify-center">
              <StreakFlame streak={me?.best_streak ?? 0} />
            </div>
            <p className="text-xs text-mist">{t("eng uzun streak")}</p>
          </div>
          <div className="rounded-2xl bg-white/[0.04] px-2 py-3">
            <p className="font-display text-xl font-bold tabular-nums">{me?.points ?? 0}</p>
            <p className="text-xs text-mist">{t("ball")}</p>
          </div>
        </div>
      )}

      <Welcome />
      {editing && data.frame && <FrameCard frame={data.frame} onSaved={refresh} />}
      <DayStrip offset={offset} onChange={setOffset} />
      <AddToRoutine
        open={adding || (asked && !pickerClosed)}
        onClose={() => {
          setAdding(false);
          setPickerClosed(true);
        }}
        onAdded={refresh}
        frame={data.frame}
      />

      {data.months.length > 0 && (
        <Card className="mb-4 flex flex-col gap-2">
          {data.months.map((m) => (
            <p key={m.participation_id} className="flex items-start gap-2 text-sm">
              <Flag className="mt-0.5 size-4 shrink-0 text-flame-400" />
              <span>
                <b>{m.title}</b> — {t("{month}-oy marrasi: {goal}", { month: m.month, goal: m.goal })}
              </span>
            </p>
          ))}
        </Card>
      )}

      {nothing ? (
        <Card>
          <EmptyState
            icon={<CalendarClock className="size-7 text-flame-400" />}
            title={data.has_life_plan ? t("Bugun dam olish kuni 🌿") : t("Birinchi maqsadingizni qo'shing")}
            body={
              data.has_life_plan
                ? t("Tiklanish ham rejaning bir qismi. Ertaga yana davom etamiz.")
                : t("Maqsad qo'shsangiz, har kuni nima qilish kerakligi shu yerda soatma-soat chiqadi.")
            }
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Button href="/routine/new">
                  <Sparkles className="size-4" /> {t("AI menga reja tuzsin")}
                </Button>
                <Button variant="secondary" onClick={() => setAdding(true)}>
                  <Plus className="size-4" /> {t("Tayyor challenge")}
                </Button>
              </div>
            }
          />
        </Card>
      ) : (
        <Card>
          <Timeline entries={entries} now={data.is_today ? now || undefined : undefined} />
          {data.untimed.length > 0 && (
            <div className="mt-6">
              <h2 className="text-sm font-semibold text-mist">{t("Vaqtsiz vazifalar")}</h2>
              <p className="mt-1 mb-3 text-xs text-mist">{t("Vaqt qo'ying — vazifa kun tartibiga tushadi va vaqtida eslataman.")}</p>
              <div className="flex flex-col gap-3">
                {data.untimed.map((item) => (
                  <TaskEntry key={`${item.participation_id}-${item.task?.key}`} item={item} onSubmitted={refresh} editing showLesson frame={data.frame} preview={!data.is_today} />
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {data.is_today && (
        <div className="mt-6 flex flex-col gap-4">
          <TelegramNudge />
          <CoachFeed limit={3} />
        </div>
      )}
    </div>
  );
}
