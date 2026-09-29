"use client";

import clsx from "clsx";
import { AnimatePresence, motion } from "motion/react";
import { Flame, Loader2, X } from "lucide-react";
import Link from "next/link";
import { forwardRef, useEffect, useId } from "react";
import { currentLocale, translate } from "@/lib/i18n";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "sky";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  href?: string;
  external?: boolean; // href opens in a new tab (Telegram, other sites)
};

const VARIANTS = {
  primary: "bg-flame text-white glow-flame hover:brightness-110",
  secondary: "glass text-white hover:bg-white/10",
  ghost: "text-mist hover:text-white hover:bg-white/5",
  danger: "bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25",
  sky: "bg-sky-500 text-white hover:bg-sky-400", // Telegram
};
const SIZES = { sm: "h-9 px-3.5 text-sm", md: "h-11 px-5", lg: "h-14 px-7 text-lg" };

export function Button({
  variant = "primary",
  size = "md",
  loading,
  href,
  external,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const classes = clsx(
    "inline-flex items-center justify-center gap-2 rounded-2xl font-semibold transition active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
    className,
  );
  if (href && external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={classes}>
        {children}
      </a>
    );
  }
  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }
  return (
    <button className={classes} disabled={disabled || loading} {...props}>
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("glass rounded-3xl p-5 sm:p-6", className)} {...props}>
      {children}
    </div>
  );
}

export function Label({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <span className="mb-1.5 flex items-baseline justify-between text-sm font-medium text-white/85">
      {children}
      {hint && <span className="text-xs font-normal text-mist">{hint}</span>}
    </span>
  );
}

const fieldClass =
  "w-full rounded-2xl border border-white/10 bg-ink-900/70 px-4 py-3 text-white placeholder:text-white/30 outline-none transition focus:border-flame-500/70 focus:ring-4 focus:ring-flame-500/15";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={clsx(fieldClass, "h-12", className)} {...props} />;
  },
);

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={clsx(fieldClass, "min-h-28 resize-none", className)} {...props} />;
}

export function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium text-white/80",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("size-6 animate-spin text-flame-400", className)} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton rounded-2xl", className)} />;
}

export function ProgressRing({
  value,
  size = 120,
  stroke = 10,
  children,
}: {
  value: number;
  size?: number;
  stroke?: number;
  children?: React.ReactNode;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#ffa24a" />
            <stop offset="55%" stopColor="#ff5f3a" />
            <stop offset="100%" stopColor="#ff3d7f" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="rgb(255 255 255 / 0.08)" strokeWidth={stroke} fill="none" />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="url(#ring)"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - clamped) }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  );
}

export function StreakFlame({ streak, size = "md" }: { streak: number; size?: "sm" | "md" | "lg" }) {
  const dims = { sm: "size-4", md: "size-6", lg: "size-10" }[size];
  const text = { sm: "text-sm", md: "text-lg", lg: "text-4xl" }[size];
  const alive = streak > 0;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Flame
        className={clsx(dims, alive ? "animate-flicker text-flame-500 drop-shadow-[0_0_10px_rgb(255_107_44/0.8)]" : "text-white/25")}
        fill={alive ? "currentColor" : "none"}
      />
      <span className={clsx("font-display font-bold tabular-nums", text, alive ? "text-flame" : "text-white/40")}>
        {streak}
      </span>
    </span>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="glass inline-flex rounded-2xl p-1">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={clsx(
            "relative rounded-xl px-3.5 py-2 text-sm font-semibold transition",
            value === option.value ? "text-white" : "text-mist hover:text-white",
          )}
        >
          {value === option.value && (
            <motion.span layoutId={`seg-${options.map((o) => o.value).join()}`} className="absolute inset-0 rounded-xl bg-white/10" />
          )}
          <span className="relative">{option.label}</span>
        </button>
      ))}
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  const titleId = useId();
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-end bg-black/60 p-0 backdrop-blur-sm sm:place-items-center sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="w-full max-w-lg rounded-t-3xl border border-white/10 bg-ink-800 p-6 shadow-2xl sm:rounded-3xl"
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 id={titleId} className="font-display text-lg font-semibold">
                {title}
              </h3>
              <button onClick={onClose} className="rounded-xl p-2 text-mist hover:bg-white/5 hover:text-white" aria-label={translate(currentLocale(), "Yopish")}>
                <X className="size-5" />
              </button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <div className="grid size-16 place-items-center rounded-3xl bg-white/5 text-3xl">{icon}</div>
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      <p className="max-w-sm text-mist">{body}</p>
      {action}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1.5 text-mist">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
