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

export async function fetchShared(token: string): Promise<Shared | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/share/${encodeURIComponent(token)}`, { next: { revalidate: 300 } });
    return response.ok ? ((await response.json()) as Shared) : null;
  } catch {
    return null;
  }
}

/** The headline of a share: the streak while it runs, the result once it is over. */
export function headline(shared: Shared): { big: string; small: string } {
  if (shared.status === "completed") return { big: `${shared.days_completed}/${shared.total_days}`, small: "kun — challenge yakunlandi! 🏆" };
  if (shared.current_streak > 0) return { big: String(shared.current_streak), small: "kun ketma-ket 🔥" };
  return { big: `${shared.days_completed}/${shared.total_days}`, small: "kun bajarildi" };
}
