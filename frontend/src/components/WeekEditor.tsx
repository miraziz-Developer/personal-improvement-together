"use client";

import clsx from "clsx";
import { Minus, Plus, Trash2 } from "lucide-react";

import { WEEKDAYS, minutes } from "@/lib/format";
import type { Task, Week } from "@/lib/types";

function newKey() {
  return `task-${Math.random().toString(36).slice(2, 8)}`;
}

export function WeekEditor({
  week,
  budgets,
  onChange,
}: {
  week: Week;
  budgets?: number[];
  onChange: (week: Week) => void;
}) {
  const update = (day: number, tasks: Task[]) => onChange(week.map((t, i) => (i === day ? tasks : t)));

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {week.map((tasks, day) => {
        const used = tasks.reduce((sum, t) => sum + t.minutes, 0);
        const budget = budgets?.[day];
        const over = budget !== undefined && used > budget;
        return (
          <div key={day} className={clsx("glass rounded-3xl p-4", tasks.length === 0 && "opacity-70")}>
            <div className="flex items-center justify-between">
              <p className="font-semibold">{WEEKDAYS[day]}</p>
              <p className={clsx("text-sm", over ? "text-danger" : "text-mist")}>
                {tasks.length ? minutes(used) : "Dam olish 🌿"}
                {budget !== undefined && ` / ${minutes(budget)}`}
              </p>
            </div>
            {budget !== undefined && budget > 0 && (
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/5">
                <div
                  className={clsx("h-full rounded-full transition-all", over ? "bg-danger" : "bg-flame")}
                  style={{ width: `${Math.min(100, (used / budget) * 100)}%` }}
                />
              </div>
            )}
            <div className="mt-3 flex flex-col gap-2">
              {tasks.map((task, index) => {
                const patch = (changes: Partial<Task>) =>
                  update(day, tasks.map((t, i) => (i === index ? { ...t, ...changes } : t)));
                return (
                  <div key={task.key} className="flex items-center gap-2 rounded-2xl bg-ink-900/60 p-2">
                    <input
                      value={task.title}
                      onChange={(e) => patch({ title: e.target.value })}
                      className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none"
                      aria-label="Vazifa nomi"
                    />
                    <div className="flex items-center rounded-xl bg-white/5">
                      <button onClick={() => patch({ minutes: Math.max(5, task.minutes - 5) })} className="p-1.5 text-mist hover:text-white" aria-label="Kamaytirish">
                        <Minus className="size-3.5" />
                      </button>
                      <span className="w-12 text-center text-xs tabular-nums">{task.minutes} daq</span>
                      <button onClick={() => patch({ minutes: Math.min(720, task.minutes + 5) })} className="p-1.5 text-mist hover:text-white" aria-label="Oshirish">
                        <Plus className="size-3.5" />
                      </button>
                    </div>
                    <button
                      onClick={() => patch({ required: !task.required })}
                      className={clsx(
                        "rounded-lg px-2 py-1 text-[11px] font-semibold",
                        task.required ? "bg-flame-500/15 text-flame-300" : "bg-white/5 text-mist",
                      )}
                    >
                      {task.required ? "Majburiy" : "Qo'shimcha"}
                    </button>
                    <button onClick={() => update(day, tasks.filter((_, i) => i !== index))} className="p-1.5 text-mist hover:text-danger" aria-label="O'chirish">
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                );
              })}
              {tasks.length < 3 && (
                <button
                  onClick={() => update(day, [...tasks, { key: newKey(), title: "Yangi vazifa", minutes: 20, required: tasks.length === 0 }])}
                  className="rounded-2xl border border-dashed border-white/10 py-2 text-sm text-mist transition hover:border-flame-500/40 hover:text-white"
                >
                  + vazifa qo'shish
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
