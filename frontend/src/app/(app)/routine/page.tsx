"use client";

import { BookOpen, CalendarClock, Flag, Plus } from "lucide-react";
import { useSyncExternalStore } from "react";
import useSWR from "swr";

import { ProofTask } from "@/components/ProofTask";
import { Timeline, type TimelineEntry } from "@/components/Timeline";
import { Button, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { shortDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Routine, RoutineItem } from "@/lib/types";

const everyMinute = (callback: () => void) => {
  const timer = setInterval(callback, 60_000);
  return () => clearInterval(timer);
};
const clockNow = () => new Date().toTimeString().slice(0, 5);

function TaskEntry({ item, onSubmitted }: { item: RoutineItem; onSubmitted: () => void }) {
  const { t } = useI18n();
  if (!item.task || !item.participation_id) return null;
  return (
    <div className="flex flex-col gap-1.5">
      <p className="px-1 text-xs text-mist">
        {item.challenge_title}
        {item.end && ` · ${t("{time} gacha", { time: item.end })}`}
      </p>
      {item.lesson && (
        <p className="flex items-center gap-1.5 px-1 text-xs text-iris">
          <BookOpen className="size-3.5" /> {item.lesson}
        </p>
      )}
      <ProofTask participationId={item.participation_id} task={item.task} onSubmitted={onSubmitted} />
    </div>
  );
}

export default function RoutinePage() {
  const { t } = useI18n();
  const { data, mutate } = useSWR<Routine>("/me/routine", { refreshInterval: 60_000 });
  const now = useSyncExternalStore(everyMinute, clockNow, () => "");

  if (!data) return <Skeleton className="h-96" />;

  const refresh = () => mutate();
  const entries: TimelineEntry[] = data.items.map((item) => ({
    kind: item.kind,
    start: item.start,
    end: item.end,
    title: item.title,
    category: item.category,
    children: item.kind === "task" ? <TaskEntry item={item} onSubmitted={refresh} /> : undefined,
  }));
  const nothing = data.items.every((i) => i.kind !== "task") && data.untimed.length === 0;

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title={t("Kun tartibi")}
        subtitle={shortDate(data.date)}
        action={
          <Button href="/routine/new" size="sm" variant="secondary">
            <Plus className="size-4" /> {data.has_life_plan ? t("Yangi kun tartibi") : t("Kun tartibini tuzish")}
          </Button>
        }
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
            title={data.has_life_plan ? t("Bugun dam olish kuni 🌿") : t("Kun tartibi hali yo'q")}
            body={
              data.has_life_plan
                ? t("Tiklanish ham rejaning bir qismi. Ertaga yana davom etamiz.")
                : t("Bir nechta maqsadingizni ayting — AI ularni bitta, soatma-soat kun tartibiga joylaydi.")
            }
            action={!data.has_life_plan && <Button href="/routine/new">{t("Kun tartibini tuzish")}</Button>}
          />
        </Card>
      ) : (
        <Card>
          <Timeline entries={entries} now={now || undefined} />
          {data.untimed.length > 0 && (
            <div className="mt-6">
              <h2 className="mb-3 text-sm font-semibold text-mist">{t("Vaqtsiz vazifalar")}</h2>
              <div className="flex flex-col gap-3">
                {data.untimed.map((item) => (
                  <TaskEntry key={`${item.participation_id}-${item.task?.key}`} item={item} onSubmitted={refresh} />
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
