// A run its owner chose to share: read on the server for the page and its pictures.
import { API_URL } from "@/lib/api";

export type Shared = {
  username: string;
  title: string;
  category: string;
  status: string;
  current_streak: number;
  best_streak: number;
  days_completed: number;
  total_days: number;
};

export const CATEGORY_EMOJI: Record<string, string> = {
  sport: "🏃",
  code: "💻",
  study: "📚",
  reading: "📖",
  health: "🌿",
  custom: "🎯",
};

export async function fetchShared(token: string, lang: "uz" | "ru" = "uz"): Promise<Shared | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/share/${encodeURIComponent(token)}?lang=${lang}`, { next: { revalidate: 300 } });
    return response.ok ? ((await response.json()) as Shared) : null;
  } catch {
    return null;
  }
}

const WORDS = {
  uz: { done: "kun — challenge yakunlandi! 🏆", streak: "kun ketma-ket 🔥", days: "kun bajarildi" },
  ru: { done: "дн. — челлендж завершён! 🏆", streak: "дн. подряд 🔥", days: "дн. выполнено" },
};

/** The headline of a share: the streak while it runs, the result once it is over. */
export function headline(shared: Shared, lang: "uz" | "ru" = "uz"): { big: string; small: string } {
  const words = WORDS[lang];
  if (shared.status === "completed") return { big: `${shared.days_completed}/${shared.total_days}`, small: words.done };
  if (shared.current_streak > 0) return { big: String(shared.current_streak), small: words.streak };
  return { big: `${shared.days_completed}/${shared.total_days}`, small: words.days };
}
