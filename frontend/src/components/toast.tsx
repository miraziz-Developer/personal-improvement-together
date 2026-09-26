"use client";

import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, Info, XCircle } from "lucide-react";
import { createContext, useCallback, useContext, useState } from "react";

type Tone = "success" | "error" | "info";
interface Toast {
  id: number;
  tone: Tone;
  title: string;
  body?: string;
}

const ToastContext = createContext<(tone: Tone, title: string, body?: string) => void>(() => {});

const ICONS = { success: CheckCircle2, error: XCircle, info: Info };
const TONES = { success: "text-mint", error: "text-danger", info: "text-flame-400" };

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((tone: Tone, title: string, body?: string) => {
    const id = Date.now() + Math.random();
    setToasts((all) => [...all, { id, tone, title, body }]);
    setTimeout(() => setToasts((all) => all.filter((t) => t.id !== id)), 5200);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-2 px-4">
        <AnimatePresence>
          {toasts.map((toast) => {
            const Icon = ICONS[toast.tone];
            return (
              <motion.div
                key={toast.id}
                initial={{ opacity: 0, y: -16, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -12, scale: 0.96 }}
                className="glass pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-2xl px-4 py-3 shadow-2xl"
              >
                <Icon className={`mt-0.5 size-5 shrink-0 ${TONES[toast.tone]}`} />
                <div>
                  <p className="font-semibold">{toast.title}</p>
                  {toast.body && <p className="mt-0.5 text-sm text-mist">{toast.body}</p>}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
